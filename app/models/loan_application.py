from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.customer import utc_now


class LoanApplication(Base):
    __tablename__ = "loan_applications"
    __table_args__ = (
        CheckConstraint("loan_amount > 0", name="ck_loan_amount_positive"),
        CheckConstraint("tenure_months > 0", name="ck_loan_tenure_positive"),
    )

    application_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    loan_type: Mapped[str] = mapped_column(String(32), default="PERSONAL", nullable=False)
    loan_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tenure_months: Mapped[int] = mapped_column(nullable=False)
    annual_interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    calculated_emi: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monthly_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    existing_emi: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    foir_percent: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    confirmation_token: Mapped[str] = mapped_column(
        String(128), ForeignKey("pending_applications.confirmation_token"), unique=True, nullable=False
    )

    def __repr__(self) -> str:
        return f"<LoanApplication {self.application_id}>"
