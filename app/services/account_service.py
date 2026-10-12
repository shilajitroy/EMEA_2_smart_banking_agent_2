from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_customer_by_id(db: Session, customer_id: str) -> Customer | None:
    return db.get(Customer, customer_id)


def get_customer_account(db: Session, customer_id: str) -> dict[str, object] | None:
    customer = get_customer_by_id(db, customer_id)
    if customer is None:
        return None
    return {
        "customer_id": customer.customer_id,
        "customer_name": customer.customer_name,
        "account_number_masked": customer.account_number_masked,
        "account_type": customer.account_type,
        "account_status": customer.account_status,
        "balance": customer.balance,
        "kyc_status": customer.kyc_status,
    }
