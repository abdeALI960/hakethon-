from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Endpoint

_DEMO_ENDPOINTS = (
    ("web", "web", 5001),
    ("api", "api", 5002),
    ("worker", "worker", 5003),
)


def is_registered_demo_target(db: Session, service: str, port: int) -> bool:
    statement = select(Endpoint.id).where(
        Endpoint.service_key == service,
        Endpoint.port == port,
        Endpoint.enabled.is_(True),
        Endpoint.is_demo_target.is_(True),
    )
    return db.scalar(statement) is not None


def seed_demo_endpoints(db: Session) -> None:
    for name, service, port in _DEMO_ENDPOINTS:
        existing = db.scalar(select(Endpoint).where(Endpoint.name == name))
        if existing is None:
            db.add(
                Endpoint(
                    name=name,
                    url=f"http://127.0.0.1:{port}",
                    service_key=service,
                    port=port,
                    probe_interval_seconds=2.0,
                    enabled=True,
                    is_demo_target=True,
                )
            )
    db.commit()
