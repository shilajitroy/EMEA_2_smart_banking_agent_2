from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def create_database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        database_path = Path(url.database)
        if not database_path.is_absolute():
            database_path = Path.cwd() / database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)

    engine_options: dict[str, object] = {"future": True}
    if url.get_backend_name() == "sqlite":
        engine_options["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            engine_options["poolclass"] = StaticPool
    engine = create_engine(database_url, **engine_options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection: Any, _record: Any) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as db:
        yield db


def init_db(engine: Engine) -> None:
    from app.models import Customer, LoanApplication, PendingApplication  # noqa: F401

    Base.metadata.create_all(bind=engine)


def seed_demo_customer(db: Session) -> None:
    from app.models.customer import Customer

    existing = db.get(Customer, "CUST1001")
    if existing is None:
        db.add(
            Customer(
                customer_id="CUST1001",
                customer_name="Rahul Sharma",
                account_number_masked="XXXXXX4582",
                account_type="Savings",
                account_status="ACTIVE",
                balance=125000.00,
                kyc_status="VERIFIED",
            )
        )
        db.commit()
