from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_token
from app.exceptions import AppError
from app.schemas.loan import (
    LoanApplicationRead,
    LoanSubmission,
    PendingApplicationCreate,
    PendingApplicationRead,
)
from app.services.application_service import (
    cancel_pending_application,
    create_pending_application,
    get_loan_application,
    submit_pending_application,
)

router = APIRouter(prefix="/api/loan-applications", tags=["loan applications"])


def _confirmation_reference(token: str) -> str:
    return f"CONF-...{token[-6:]}"


@router.post(
    "/pending",
    response_model=PendingApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an application pending explicit confirmation",
)
def prepare_application(
    payload: PendingApplicationCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_token),
) -> PendingApplicationRead:
    pending = create_pending_application(
        db,
        customer_id=payload.customer_id,
        loan_amount=payload.loan_amount,
        tenure_months=payload.tenure_months,
        annual_interest_rate=payload.annual_interest_rate,
        monthly_salary=payload.monthly_salary,
        existing_emi=payload.existing_emi,
        calculated_emi=payload.calculated_emi,
        foir_percent=payload.foir_percent,
        eligible=payload.eligible,
    )
    return PendingApplicationRead(
        confirmation_token=pending.confirmation_token,
        confirmation_reference=_confirmation_reference(pending.confirmation_token),
        customer_id=pending.customer_id,
        loan_amount=pending.loan_amount,
        tenure_months=pending.tenure_months,
        annual_interest_rate=pending.annual_interest_rate,
        calculated_emi=pending.calculated_emi,
        monthly_salary=pending.monthly_salary,
        existing_emi=pending.existing_emi,
        foir_percent=pending.foir_percent,
        eligible=pending.eligible,
        status=pending.status,
        expires_at=pending.expires_at.isoformat(),
    )


@router.post(
    "/submit",
    response_model=LoanApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a loan application after explicit confirmation",
)
def submit_application(
    payload: LoanSubmission,
    response: Response,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_token),
) -> LoanApplicationRead:
    application, idempotent = submit_pending_application(
        db,
        customer_id=payload.customer_id,
        confirmation_token=payload.confirmation_token,
        confirmed=payload.confirmed,
    )
    if idempotent:
        response.status_code = status.HTTP_200_OK
    created_at = application.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return LoanApplicationRead(
        application_id=application.application_id,
        customer_id=application.customer_id,
        loan_type=application.loan_type,
        loan_amount=application.loan_amount,
        tenure_months=application.tenure_months,
        annual_interest_rate=application.annual_interest_rate,
        calculated_emi=application.calculated_emi,
        monthly_salary=application.monthly_salary,
        existing_emi=application.existing_emi,
        foir_percent=application.foir_percent,
        status=application.status,
        created_at=created_at.isoformat(),
        idempotent=idempotent,
    )


@router.get(
    "/{application_id}",
    response_model=LoanApplicationRead,
    summary="Retrieve a submitted loan application",
)
def read_application(
    application_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_token),
) -> LoanApplicationRead:
    application = get_loan_application(db, application_id)
    if application is None:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Loan application was not found.")
    created_at = application.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return LoanApplicationRead(
        application_id=application.application_id,
        customer_id=application.customer_id,
        loan_type=application.loan_type,
        loan_amount=application.loan_amount,
        tenure_months=application.tenure_months,
        annual_interest_rate=application.annual_interest_rate,
        calculated_emi=application.calculated_emi,
        monthly_salary=application.monthly_salary,
        existing_emi=application.existing_emi,
        foir_percent=application.foir_percent,
        status=application.status,
        created_at=created_at.isoformat(),
    )


@router.post(
    "/{confirmation_token}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel an application awaiting confirmation",
)
def cancel_application(
    confirmation_token: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_token),
) -> dict[str, object]:
    pending = cancel_pending_application(db, confirmation_token)
    return {
        "success": True,
        "confirmation_reference": _confirmation_reference(pending.confirmation_token),
        "status": pending.status,
    }
