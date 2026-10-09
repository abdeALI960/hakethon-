from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import settings
from backend.database import get_db
from backend.main import create_app
from backend.middleware import _rate_limiter
from backend.models import Base


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(settings, "database_url", "sqlite:///:memory:")
    monkeypatch.setattr(settings, "monitor_enabled", False)
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr("backend.main.create_all", lambda: None)

    def override_get_db() -> Iterator[Session]:
        with db_factory() as db:
            yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    _rate_limiter._hits.clear()
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            app=app,
            db_factory=db_factory,
            engine=engine,
        )
    app.dependency_overrides.clear()
    _rate_limiter._hits.clear()
    engine.dispose()


@pytest.fixture
def temp_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "inspector.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    return path
