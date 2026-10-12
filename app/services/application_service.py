from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import AppError
from app.models.customer import Customer, utc_now
from app.models.loan_application import LoanApplication
from app.models.pending_application import PendingApplication
from app.services.emi_service import calculate_loan_emi, money, to_decimal
from app.services.eligibility_service import verify_loan_eligibility


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _terms_match(
    pending: PendingApplication,
    *,
    amount: Decimal,
    tenure_months: int,
    annual_interest_rate: Decimal,
    monthly_salary: Decimal,
    existing_emi: Decimal,
) -> bool:
    return (
        pending.loan_amount == amount
        and pending.tenure_months == tenure_months
        and pending.annual_interest_rate == annual_interest_rate
        and pending.monthly_salary == monthly_salary
        and pending.existing_emi == existing_emi
    )


def create_pending_application(
    db: Session,
    *,
    customer_id: str,
    loan_amount: Decimal | float | int | str,
    tenure_months: int,
    annual_interest_rate: Decimal | float | int | str,
    monthly_salary: Decimal | float | int | str,
    existing_emi: Decimal | float | int | str,
    calculated_emi: Decimal | float | int | str,
    foir_percent: Decimal | float | int | str,
    eligible: bool,
) -> PendingApplication:
    amount = money(loan_amount)
    rate = to_decimal(annual_interest_rate)
    salary = money(monthly_salary)
    prior_emi = money(existing_emi)
    emi_result = calculate_loan_emi(amount, tenure_months, rate)
    server_emi = emi_result["monthly_emi"]
    assert isinstance(server_emi, Decimal)
    eligibility = verify_loan_eligibility(amount, salary, prior_emi, server_emi)
    server_foir = eligibility["foir_percent"]
    assert isinstance(server_foir, Decimal)

    if money(calculated_emi) != server_emi or money(foir_percent) != server_foir:
        raise AppError(422, "TERMS_MISMATCH", "Provided loan calculations do not match server calculations.")
    if eligible is not eligibility["eligible"]:
        raise AppError(422, "ELIGIBILITY_MISMATCH", "Provided eligibility result does not match server validation.")
    if not eligibility["eligible"]:
        reasons = "; ".join(eligibility["reasons"])  # type: ignore[arg-type]
        raise AppError(422, "INELIGIBLE", reasons)

    try:
        with db.begin():
            customer = db.get(Customer, customer_id)
            if customer is None:
                raise AppError(404, "CUSTOMER_NOT_FOUND", "Customer was not found.")
            if customer.account_status != "ACTIVE":
                raise AppError(422, "ACCOUNT_INACTIVE", "The customer's account is not active.")
            if customer.kyc_status != "VERIFIED":
                raise AppError(422, "KYC_NOT_VERIFIED", "The customer's KYC is not verified.")

            now = utc_now()
            existing = list(
                db.scalars(
                    select(PendingApplication).where(
                        PendingApplication.customer_id == customer_id,
                        PendingApplication.status == "AWAITING_CONFIRMATION",
                    )
                )
            )
            for previous in existing:
                if _terms_match(
                    previous,
                    amount=amount,
                    tenure_months=tenure_months,
                    annual_interest_rate=rate,
                    monthly_salary=salary,
                    existing_emi=prior_emi,
                ) and _utc(previous.expires_at) > now:
                    return previous
                previous.status = "CANCELLED"
                previous.cancelled_at = now

            pending = PendingApplication(
                confirmation_token=secrets.token_urlsafe(32),
                customer_id=customer_id,
                loan_amount=amount,
                tenure_months=tenure_months,
                annual_interest_rate=rate,
                calculated_emi=server_emi,
                monthly_salary=salary,
                existing_emi=prior_emi,
                foir_percent=server_foir,
                eligible=True,
                status="AWAITING_CONFIRMATION",
                expires_at=now + timedelta(minutes=settings.confirmation_expiry_minutes),
            )
            db.add(pending)
            db.flush()
            return pending
    except IntegrityError as exc:
        raise AppError(409, "PENDING_APPLICATION_CONFLICT", "Could not prepare the pending application.") from exc


def get_pending_application(db: Session, confirmation_token: str) -> PendingApplication | None:
    return db.scalar(
        select(PendingApplication).where(PendingApplication.confirmation_token == confirmation_token)
    )


def submit_pending_application(
    db: Session,
    *,
    customer_id: str,
    confirmation_token: str,
    confirmed: bool,
) -> tuple[LoanApplication, bool]:
    if confirmed is not True:
        raise AppError(409, "CONFIRMATION_REQUIRED", "Explicit customer confirmation is required.")

    try:
        with db.begin():
            existing_application = db.scalar(
                select(LoanApplication).where(
                    LoanApplication.confirmation_token == confirmation_token
                )
            )
            if existing_application is not None:
                if existing_application.customer_id != customer_id:
                    raise AppError(404, "APPLICATION_NOT_FOUND", "Application was not found.")
                return existing_application, True

            pending = get_pending_application(db, confirmation_token)
            if pending is None or pending.customer_id != customer_id:
                raise AppError(404, "CONFIRMATION_NOT_FOUND", "Confirmation reference was not found.")
            if pending.status == "CANCELLED" or pending.cancelled_at is not None:
                raise AppError(409, "CONFIRMATION_CANCELLED", "This confirmation has been cancelled.")
            if pending.status == "SUBMITTED":
                raise AppError(409, "APPLICATION_STATE_CONFLICT", "This application has already been submitted.")
            if _utc(pending.expires_at) <= utc_now():
                raise AppError(410, "CONFIRMATION_EXPIRED", "This confirmation reference has expired.")
            if pending.status != "AWAITING_CONFIRMATION" or pending.used_at is not None:
                raise AppError(409, "APPLICATION_STATE_CONFLICT", "This application is not awaiting confirmation.")
            customer = db.get(Customer, customer_id)
            if customer is None:
                raise AppError(404, "CUSTOMER_NOT_FOUND", "Customer was not found.")
            if customer.account_status != "ACTIVE":
                raise AppError(422, "ACCOUNT_INACTIVE", "The customer's account is not active.")
            if customer.kyc_status != "VERIFIED":
                raise AppError(422, "KYC_NOT_VERIFIED", "The customer's KYC is not verified.")

            recalculated = calculate_loan_emi(
                pending.loan_amount, pending.tenure_months, pending.annual_interest_rate
            )["monthly_emi"]
            eligibility = verify_loan_eligibility(
                pending.loan_amount,
                pending.monthly_salary,
                pending.existing_emi,
                recalculated,
            )
            if (
                recalculated != pending.calculated_emi
                or eligibility["foir_percent"] != pending.foir_percent
                or eligibility["eligible"] is not True
                or pending.eligible is not True
            ):
                raise AppError(409, "TERMS_CHANGED", "Stored terms have changed; recalculate and confirm again.")

            application = LoanApplication(
                application_id=f"PL-{secrets.token_hex(5).upper()}",
                customer_id=pending.customer_id,
                loan_type="PERSONAL",
                loan_amount=pending.loan_amount,
                tenure_months=pending.tenure_months,
                annual_interest_rate=pending.annual_interest_rate,
                calculated_emi=pending.calculated_emi,
                monthly_salary=pending.monthly_salary,
                existing_emi=pending.existing_emi,
                foir_percent=pending.foir_percent,
                status="SUBMITTED",
                confirmation_token=pending.confirmation_token,
            )
            pending.status = "SUBMITTED"
            pending.used_at = utc_now()
            db.add(application)
            db.flush()
            return application, False
    except IntegrityError as exc:
        db.rollback()
        existing_application = db.scalar(
            select(LoanApplication).where(
                LoanApplication.confirmation_token == confirmation_token
            )
        )
        if existing_application is not None and existing_application.customer_id == customer_id:
            return existing_application, True
        raise AppError(409, "APPLICATION_CONFLICT", "The application could not be submitted.") from exc


def cancel_pending_application(
    db: Session, confirmation_token: str, customer_id: str | None = None
) -> PendingApplication:
    with db.begin():
        pending = get_pending_application(db, confirmation_token)
        if pending is None or (customer_id is not None and pending.customer_id != customer_id):
            raise AppError(404, "CONFIRMATION_NOT_FOUND", "Confirmation reference was not found.")
        if pending.status == "SUBMITTED":
            raise AppError(409, "APPLICATION_ALREADY_SUBMITTED", "A submitted application cannot be cancelled here.")
        if pending.status != "AWAITING_CONFIRMATION":
            raise AppError(409, "APPLICATION_STATE_CONFLICT", "This application is not awaiting confirmation.")
        pending.status = "CANCELLED"
        pending.cancelled_at = utc_now()
        db.flush()
        return pending


def get_loan_application(db: Session, application_id: str) -> LoanApplication | None:
    return db.get(LoanApplication, application_id)
