from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    account_number_masked: Mapped[str] = mapped_column(String(24), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    account_status: Mapped[str] = mapped_column(String(24), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    kyc_status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Customer {self.customer_id}>"
