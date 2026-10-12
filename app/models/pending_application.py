from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.customer import utc_now


class PendingApplication(Base):
    __tablename__ = "pending_applications"
    __table_args__ = (
        CheckConstraint("loan_amount > 0", name="ck_pending_loan_amount_positive"),
        CheckConstraint("tenure_months > 0", name="ck_pending_tenure_positive"),
        CheckConstraint("annual_interest_rate > 0", name="ck_pending_rate_positive"),
        CheckConstraint("monthly_salary > 0", name="ck_pending_salary_positive"),
        CheckConstraint("existing_emi >= 0", name="ck_pending_existing_emi_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    confirmation_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    loan_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tenure_months: Mapped[int] = mapped_column(nullable=False)
    annual_interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    calculated_emi: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monthly_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    existing_emi: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    foir_percent: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="AWAITING_CONFIRMATION", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<PendingApplication {self.id}:{self.status}>"
