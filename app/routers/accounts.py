from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_token
from app.exceptions import AppError
from app.schemas.customer import AccountRead
from app.services.account_service import get_customer_account

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/{customer_id}", response_model=AccountRead, summary="Retrieve masked customer account details")
def get_account(
    customer_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_token),
) -> AccountRead:
    account = get_customer_account(db, customer_id)
    if account is None:
        raise AppError(404, "CUSTOMER_NOT_FOUND", "Customer was not found.")
    return AccountRead.model_validate(account)
