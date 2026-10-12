from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.services.emi_service import DEFAULT_ANNUAL_INTEREST_RATE


class PendingApplicationCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=32)
    loan_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    tenure_months: int = Field(gt=0, le=600)
    annual_interest_rate: Decimal = Field(
        default=DEFAULT_ANNUAL_INTEREST_RATE, gt=0, max_digits=7, decimal_places=3
    )
    monthly_salary: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    existing_emi: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    calculated_emi: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    foir_percent: Decimal = Field(ge=0, max_digits=7, decimal_places=2)
    eligible: bool


class PendingApplicationRead(BaseModel):
    success: bool = True
    confirmation_token: str
    confirmation_reference: str
    customer_id: str
    loan_amount: Decimal
    tenure_months: int
    annual_interest_rate: Decimal
    calculated_emi: Decimal
    monthly_salary: Decimal
    existing_emi: Decimal
    foir_percent: Decimal
    eligible: bool
    status: str
    expires_at: str


class LoanSubmission(BaseModel):
    customer_id: str = Field(min_length=1, max_length=32)
    confirmation_token: str = Field(min_length=20, max_length=128)
    confirmed: bool


class LoanApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    application_id: str
    customer_id: str
    loan_type: str
    loan_amount: Decimal
    tenure_months: int
    annual_interest_rate: Decimal
    calculated_emi: Decimal
    monthly_salary: Decimal
    existing_emi: Decimal
    foir_percent: Decimal
    status: str
    created_at: str
    idempotent: bool = False
