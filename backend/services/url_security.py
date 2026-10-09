import asyncio
import ipaddress
import socket
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import AppError
from backend.models import Endpoint

_DEMO_HOST_PORTS = {
    ("127.0.0.1", 5001),
    ("127.0.0.1", 5002),
    ("127.0.0.1", 5003),
    ("localhost", 5001),
    ("localhost", 5002),
    ("localhost", 5003),
    ("::1", 5001),
    ("::1", 5002),
    ("[::1]", 5001),
    ("[::1]", 5002),
    ("[::1]", 5003),
}


def _host_port(url: str) -> tuple[str, int]:
    parsed = urlsplit(url)
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise AppError("INVALID_URL", "URL port is invalid.", 422) from exc
    return (parsed.hostname or "").lower().rstrip("."), port


def _registered_endpoint(db: Session, url: str) -> Endpoint | None:
    normalized = urlunsplit(
        (
            urlsplit(url).scheme.lower(),
            urlsplit(url).netloc.lower(),
            urlsplit(url).path.rstrip("/"),
            urlsplit(url).query,
            "",
        )
    )
    for endpoint in db.scalars(select(Endpoint)).all():
        existing = urlsplit(endpoint.url)
        existing_normalized = urlunsplit(
            (
                existing.scheme.lower(),
                existing.netloc.lower(),
                existing.path.rstrip("/"),
                existing.query,
                "",
            )
        )
        if normalized == existing_normalized:
            return endpoint
    return None


def _validate_url_shape(url: str, *, https_only: bool = False):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise AppError("INVALID_URL", "URL is invalid.", 422) from exc
    scheme = parsed.scheme.lower()
    if scheme not in ({"https"} if https_only else {"http", "https"}):
        allowed = "HTTPS" if https_only else "HTTP or HTTPS"
        raise AppError("INVALID_URL", f"URL must use {allowed}.", 422)
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise AppError("INVALID_URL", "URL must not contain credentials or fragments.", 422)
    if any(character in url for character in "\r\n\t"):
        raise AppError("INVALID_URL", "URL contains invalid characters.", 422)
    secret_keys = {
        "api_key",
        "apikey",
        "password",
        "passwd",
        "pwd",
        "token",
        "access_token",
        "auth_token",
        "secret",
        "client_secret",
    }
    if any(key.lower() in secret_keys for key, _ in parse_qsl(parsed.query)):
        raise AppError("INVALID_URL", "URLs must not include secret query parameters.", 422)
    return parsed


def _resolve_and_check_public(url: str) -> None:
    parsed = urlsplit(url)
    hostname = parsed.hostname
    if hostname is None:
        raise AppError("INVALID_URL", "URL hostname is required.", 422)
    try:
        literal = ipaddress.ip_address(hostname)
        addresses = [literal]
    except ValueError:
        try:
            info = socket.getaddrinfo(
                hostname,
                parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise AppError("TARGET_DNS_FAILED", "Target hostname could not be resolved.", 422) from exc
        addresses = []
        for entry in info:
            try:
                addresses.append(ipaddress.ip_address(entry[4][0]))
            except ValueError:
                continue
    if not addresses:
        raise AppError("TARGET_DNS_FAILED", "Target hostname has no usable addresses.", 422)
    if any(not address.is_global for address in addresses):
        raise AppError("SSRF_BLOCKED", "Target resolves to a non-public IP address.", 403)


async def validate_target_url(
    db: Session,
    url: str,
    *,
    https_only: bool = False,
    allow_registered: bool = True,
) -> None:
    _validate_url_shape(url, https_only=https_only)
    registered = _registered_endpoint(db, url) if allow_registered else None
    if registered is not None:
        return
    if _host_port(url) in _DEMO_HOST_PORTS:
        demo = db.scalar(
            select(Endpoint.id).where(
                Endpoint.port == _host_port(url)[1],
                Endpoint.is_demo_target.is_(True),
                Endpoint.enabled.is_(True),
            )
        )
        if demo is not None:
            return
    await asyncio.to_thread(_resolve_and_check_public, url)
