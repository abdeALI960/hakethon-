import json
import logging
import math
import os
import secrets
import sys
import time
from collections import defaultdict, deque
from typing import Any
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.config import settings

_LOGGER = logging.getLogger("opspilot.http")
_MAX_BODY_BYTES = 6 * 1024 * 1024
_MAX_JSON_DEPTH = 20
_MAX_JSON_STRING_LENGTH = 10_000
_RATE_RULES: dict[str, tuple[int, int]] = {
    "/api/analyze": (10, 60),
    "/analyze": (10, 60),
    "/api/emergency/intake": (10, 60),
    "/api/chaos/inject": (5, 60),
    "/api/probe": (60, 60),
}
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


class _RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def consume(
        self,
        client: str,
        path: str,
        now: float,
    ) -> int | None:
        rule = _RATE_RULES.get(path)
        if rule is None:
            return None
        limit, window_seconds = rule
        key = (client, path)
        hits = self._hits[key]
        cutoff = now - window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return max(1, math.ceil(window_seconds - (now - hits[0])))
        hits.append(now)
        if len(self._hits) > 10_000:
            for stale_key in tuple(self._hits):
                stale_hits = self._hits[stale_key]
                while stale_hits and stale_hits[0] <= cutoff:
                    stale_hits.popleft()
                if not stale_hits:
                    self._hits.pop(stale_key, None)
        return None


_rate_limiter = _RateLimiter()


def _json_log(level: int, event: str, **fields: Any) -> None:
    _LOGGER.log(
        level,
        event,
        extra={"structured_fields": fields},
    )


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "structured_fields", {})
        return json.dumps(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
                "level": record.levelname,
                "logger": record.name,
                **fields,
                "message": record.getMessage(),
            },
            separators=(",", ":"),
            ensure_ascii=True,
        )


def configure_structured_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        root.addHandler(handler)
    for handler in root.handlers:
        handler.setFormatter(_JsonLogFormatter())


def _configured_bind_host() -> str:
    bind_host = os.environ.get("HOST") or os.environ.get("OPSPILOT_BIND_HOST")
    if bind_host:
        return bind_host
    for index, argument in enumerate(sys.argv):
        if argument == "--host" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if argument.startswith("--host="):
            return argument.partition("=")[2]
    return "127.0.0.1"


def startup_self_check() -> None:
    provider_keys = {
        "openai": bool(settings.openai_api_key and settings.openai_api_key.get_secret_value()),
        "anthropic": bool(
            settings.anthropic_api_key and settings.anthropic_api_key.get_secret_value()
        ),
        "gemini": bool(settings.gemini_api_key and settings.gemini_api_key.get_secret_value()),
    }
    _json_log(
        logging.INFO,
        "startup_self_check",
        llm_provider_keys=provider_keys,
        chaos_enabled=settings.chaos_enabled,
        auth_enabled=settings.auth_enabled,
    )
    bind_host = _configured_bind_host()
    if settings.chaos_enabled and not settings.auth_enabled and bind_host not in _LOCAL_HOSTS:
        _json_log(
            logging.WARNING,
            "unsafe_chaos_bind",
            bind_host=bind_host,
            warning="CHAOS_ENABLED is active on a non-local bind without API authentication.",
        )


def _too_deep_or_long(value: Any) -> bool:
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > _MAX_JSON_DEPTH:
            return True
        if isinstance(current, str) and len(current) > _MAX_JSON_STRING_LENGTH:
            return True
        if isinstance(current, dict):
            for key, item in current.items():
                if isinstance(key, str) and len(key) > _MAX_JSON_STRING_LENGTH:
                    return True
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return False


def _error_response(
    status: int,
    code: str,
    message: str,
    request_id: str,
    *,
    retry_after: int | None = None,
) -> Message:
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", b"0"),
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"no-referrer"),
        (b"x-request-id", request_id.encode("ascii")),
    ]
    body = json.dumps(
        {"error": {"code": code, "message": message}},
        separators=(",", ":"),
    ).encode()
    headers[1] = (b"content-length", str(len(body)).encode())
    if retry_after is not None:
        headers.append((b"retry-after", str(retry_after).encode()))
    return {
        "type": "http.response.start",
        "status": status,
        "headers": headers,
        "_body": body,
    }


async def _send_error(send: Send, response: Message) -> None:
    body = response.pop("_body")
    await send(response)
    await send({"type": "http.response.body", "body": body, "more_body": False})


class BackendHardeningMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._bind_checked = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        supplied_id = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore").strip()
        request_id = (
            supplied_id
            if supplied_id and len(supplied_id) <= 128
            and all(char.isalnum() or char in "._:-" for char in supplied_id)
            else str(uuid4())
        )
        scope.setdefault("state", {})["request_id"] = request_id
        server = scope.get("server")
        if not self._bind_checked:
            self._bind_checked = True
            if server and settings.chaos_enabled and not settings.auth_enabled:
                host = str(server[0]).strip("[]")
                if host not in _LOCAL_HOSTS:
                    _json_log(
                        logging.WARNING,
                        "unsafe_chaos_bind",
                        bind_host=host,
                        warning=(
                            "CHAOS_ENABLED is active on a non-local bind without "
                            "API authentication."
                        ),
                    )

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                scope.setdefault("state", {})["response_status"] = message["status"]
                response_headers = list(message.get("headers", []))
                existing_headers = {key.lower() for key, _value in response_headers}
                for key, value in (
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-request-id", request_id.encode("ascii")),
                ):
                    if key not in existing_headers:
                        response_headers.append((key, value))
                message["headers"] = response_headers
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                _json_log(
                    logging.INFO,
                    "http_request",
                    method=method,
                    route=getattr(scope.get("route"), "path", "unmatched"),
                    status=scope.get("state", {}).get("response_status"),
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                )
            await send(message)

        protected_route = path.startswith("/api/") or path == "/analyze"
        if settings.auth_enabled and protected_route and method != "OPTIONS":
            provided_key = headers.get(b"x-api-key", b"").decode("latin-1")
            configured_key = (
                settings.api_key.get_secret_value()
                if settings.api_key is not None
                else ""
            )
            if not configured_key or not secrets.compare_digest(provided_key, configured_key):
                await _send_error(
                    send_with_headers,
                    _error_response(
                        401,
                        "UNAUTHORIZED",
                        "A valid API key is required.",
                        request_id,
                    ),
                )
                return

        client = scope.get("client")
        client_key = str(client[0]) if client else "unknown"
        retry_after = (
            None
            if method == "OPTIONS"
            else _rate_limiter.consume(client_key, path, time.monotonic())
        )
        if retry_after is not None:
            await _send_error(
                send_with_headers,
                _error_response(
                    429,
                    "RATE_LIMITED",
                    "Too many requests. Retry after the indicated delay.",
                    request_id,
                    retry_after=retry_after,
                ),
            )
            return

        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > _MAX_BODY_BYTES:
                    await _send_error(
                        send_with_headers,
                        _error_response(
                            413,
                            "REQUEST_TOO_LARGE",
                            "Request body may not exceed 6 MB.",
                            request_id,
                        ),
                    )
                    return
            except ValueError:
                await _send_error(
                    send_with_headers,
                    _error_response(
                        400,
                        "INVALID_CONTENT_LENGTH",
                        "Content-Length header is invalid.",
                        request_id,
                    ),
                )
                return

        chunks: list[bytes] = []
        body_size = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            body_size += len(chunk)
            if body_size > _MAX_BODY_BYTES:
                await _send_error(
                    send_with_headers,
                    _error_response(
                        413,
                        "REQUEST_TOO_LARGE",
                        "Request body may not exceed 6 MB.",
                        request_id,
                    ),
                )
                return
            chunks.append(chunk)
            more_body = message.get("more_body", False)
        body = b"".join(chunks)

        content_type = headers.get(b"content-type", b"").lower()
        if body and (
            content_type.startswith(b"application/json")
            or b"+json" in content_type.split(b";", 1)[0]
        ):
            depth_error = False
            try:
                parsed_body = json.loads(body)
            except RecursionError:
                parsed_body = None
                depth_error = True
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed_body = None
            if depth_error or (
                parsed_body is not None and _too_deep_or_long(parsed_body)
            ):
                await _send_error(
                    send_with_headers,
                    _error_response(
                        422,
                        "VALIDATION_ERROR",
                        "JSON nesting or string length exceeds the allowed limit.",
                        request_id,
                    ),
                )
                return

        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send_with_headers)
