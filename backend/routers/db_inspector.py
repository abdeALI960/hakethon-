import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.engine import make_url

from backend.config import settings
from backend.errors import AppError
from backend.schemas import (
    DbExportResponse,
    DbSchemaResponse,
    DbTableInfo,
    DbTableRowsResponse,
    DbTableSchema,
    DbTablesResponse,
)
from backend.services.redaction import redact_text

router = APIRouter()

ALLOWLISTED_TABLES = (
    "endpoints",
    "probe_results",
    "incidents",
    "incident_logs",
    "analyses",
    "remediations",
    "emergency_cases",
    "settings",
)
EXPORT_ROW_CAP = 10_000
_IDENTIFIER_QUOTES = '"'
_SECRET_COLUMN_MARKERS = ("password", "passwd", "token", "secret", "api_key", "credential")


def _readonly_connection() -> sqlite3.Connection:
    database_url = make_url(settings.database_url)
    if database_url.get_backend_name() != "sqlite":
        raise AppError(
            "DB_INSPECTOR_UNAVAILABLE",
            "The read-only inspector requires a SQLite database.",
            503,
        )
    database_path = database_url.database
    if not database_path or database_path == ":memory:":
        raise AppError(
            "DB_INSPECTOR_UNAVAILABLE",
            "The SQLite database must be a file to open it read-only.",
            503,
        )
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise AppError("DATABASE_NOT_FOUND", "The SQLite database file was not found.", 503)
    uri = f"file:{quote(path.as_posix(), safe='/')}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        return connection
    except sqlite3.Error as exc:
        raise AppError(
            "DB_INSPECTOR_UNAVAILABLE",
            "Could not open the SQLite database in read-only mode.",
            503,
        ) from exc


def _available_tables(connection: sqlite3.Connection) -> tuple[str, ...]:
    placeholders = ",".join("?" for _ in ALLOWLISTED_TABLES)
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        f"WHERE type = 'table' AND name IN ({placeholders})",
        ALLOWLISTED_TABLES,
    ).fetchall()
    existing = {row["name"] for row in rows}
    return tuple(name for name in ALLOWLISTED_TABLES if name in existing)


def _quote_identifier(identifier: str) -> str:
    if identifier not in ALLOWLISTED_TABLES:
        raise AppError("INVALID_TABLE", "Table is not available for inspection.", 404)
    return f'{_IDENTIFIER_QUOTES}{identifier}{_IDENTIFIER_QUOTES}'


def _redact_column(table: str, column: str, value: Any) -> Any:
    if value is None:
        return None
    if any(marker in column.lower() for marker in _SECRET_COLUMN_MARKERS):
        return "[REDACTED]"
    if column == "evidence_path":
        return "[REDACTED]"
    if column == "webhook_url" and isinstance(value, str):
        if "?" in value:
            value = f"{value.split('?', 1)[0]}?[REDACTED]"
        return redact_text(value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def _row_dict(table: str, row: sqlite3.Row) -> dict[str, Any]:
    return {
        column: _redact_column(table, column, row[column])
        for column in row.keys()
    }


def _text_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    quoted = _quote_identifier(table)
    return [
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({quoted})")
        if "CHAR" in row["type"].upper()
        or "CLOB" in row["type"].upper()
        or "TEXT" in row["type"].upper()
    ]


@router.get("/db/tables", response_model=DbTablesResponse)
def list_tables() -> DbTablesResponse:
    with closing(_readonly_connection()) as connection:
        tables = _available_tables(connection)
        return DbTablesResponse(
            tables=[
                DbTableInfo(
                    name=table,
                    row_count=connection.execute(
                        f"SELECT COUNT(*) FROM {_quote_identifier(table)}"
                    ).fetchone()[0],
                )
                for table in tables
            ]
        )


@router.get("/db/tables/{name}", response_model=DbTableRowsResponse)
def get_table_rows(
    name: str,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200),
) -> DbTableRowsResponse:
    if name not in ALLOWLISTED_TABLES:
        raise AppError("INVALID_TABLE", "Table is not available for inspection.", 404)
    with closing(_readonly_connection()) as connection:
        if name not in _available_tables(connection):
            raise AppError("INVALID_TABLE", "Table is not available for inspection.", 404)
        quoted = _quote_identifier(name)
        filters: list[str] = []
        parameters: list[Any] = []
        if q:
            columns = _text_columns(connection, name)
            if columns:
                filters.append(
                    "("
                    + " OR ".join(f'"{column}" LIKE ? ESCAPE \'\\\'' for column in columns)
                    + ")"
                )
                escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                parameters.extend([f"%{escaped_q}%"] * len(columns))
            else:
                filters.append("0")
        where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
        total = connection.execute(
            f"SELECT COUNT(*) FROM {quoted}{where_clause}",
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"SELECT * FROM {quoted}{where_clause} LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        ).fetchall()
        return DbTableRowsResponse(
            table=name,
            rows=[_row_dict(name, row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
            q=q,
        )


@router.get("/db/schema", response_model=DbSchemaResponse)
def get_schema() -> DbSchemaResponse:
    with closing(_readonly_connection()) as connection:
        tables = _available_tables(connection)
        if not tables:
            return DbSchemaResponse(tables=[])
        placeholders = ",".join("?" for _ in tables)
        rows = connection.execute(
            "SELECT name, sql FROM sqlite_master "
            f"WHERE type = 'table' AND name IN ({placeholders})",
            tables,
        ).fetchall()
        create_statements = {row["name"]: row["sql"] for row in rows}
        return DbSchemaResponse(
            tables=[
                DbTableSchema(name=table, create_sql=create_statements[table])
                for table in tables
                if create_statements.get(table)
            ]
        )


def _iter_export(connection: sqlite3.Connection) -> Iterator[str]:
    encoder = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))
    tables = _available_tables(connection)
    total_available = sum(
        connection.execute(
            f"SELECT COUNT(*) FROM {_quote_identifier(table)}"
        ).fetchone()[0]
        for table in tables
    )
    truncated = total_available > EXPORT_ROW_CAP
    emitted = 0
    yield '{"tables":{'
    for table_index, table in enumerate(tables):
        if table_index:
            yield ","
        yield from encoder.iterencode(table)
        yield ":["
        remaining = EXPORT_ROW_CAP - emitted
        rows = connection.execute(
            f"SELECT * FROM {_quote_identifier(table)} LIMIT ?",
            (remaining,),
        )
        for table_row_count, row in enumerate(rows):
            if table_row_count:
                yield ","
            yield from encoder.iterencode(_row_dict(table, row))
            emitted += 1
        yield "]"
    yield '},"rowCount":'
    yield str(emitted)
    yield ',"rowCap":'
    yield str(EXPORT_ROW_CAP)
    yield ',"truncated":'
    yield "true" if truncated else "false"
    yield "}"


def _export_chunks(connection: sqlite3.Connection) -> Iterator[str]:
    try:
        yield from _iter_export(connection)
    finally:
        connection.close()


@router.get(
    "/db/export",
    response_class=StreamingResponse,
    response_model=DbExportResponse,
    responses={200: {"content": {"application/json": {"schema": DbExportResponse.model_json_schema()}}}},
)
def export_tables() -> StreamingResponse:
    connection = _readonly_connection()
    return StreamingResponse(
        _export_chunks(connection),
        media_type="application/json",
    )
