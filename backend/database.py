from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models import Base, RuntimeSettings
from backend.repositories.endpoints import seed_demo_endpoints

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)


@event.listens_for(engine, "connect")
def configure_sqlite_connection(connection, _connection_record) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("emergency_cases")}
    if "llm_status" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE emergency_cases "
                    "ADD COLUMN llm_status VARCHAR(16) NOT NULL DEFAULT 'failed'"
                )
            )
    with SessionLocal() as db:
        seed_demo_endpoints(db)
        if db.scalar(select(RuntimeSettings.id).limit(1)) is None:
            db.add(
                RuntimeSettings(
                    id=1,
                    llm_provider=settings.llm_provider,
                    zero_touch_enabled=settings.zero_touch_default,
                )
            )
            db.commit()
