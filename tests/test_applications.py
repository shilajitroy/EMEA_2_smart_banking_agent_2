from datetime import timedelta

import pytest

from app.models.customer import Customer
from app.models.pending_application import PendingApplication
from app.models.customer import utc_now
from app.services.emi_service import calculate_loan_emi
from app.services.eligibility_service import verify_loan_eligibility


def pending_payload(
    *,
    customer_id: str = "CUST1001",
    loan_amount: str = "500000.00",
    monthly_salary: str = "60000.00",
    existing_emi: str = "5000.00",
) -> dict[str, object]:
    emi = calculate_loan_emi(loan_amount, 36, "12")
    eligibility = verify_loan_eligibility(
        loan_amount, monthly_salary, existing_emi, emi["monthly_emi"]
    )
    return {
        "customer_id": customer_id,
        "loan_amount": loan_amount,
        "tenure_months": 36,
        "annual_interest_rate": "12",
        "monthly_salary": monthly_salary,
        "existing_emi": existing_emi,
        "calculated_emi": str(emi["monthly_emi"]),
        "foir_percent": str(eligibility["foir_percent"]),
        "eligible": eligibility["eligible"],
    }


def _create_pending(client, auth_headers, **overrides):
    payload = pending_payload(**overrides)
    response = client.post(
        "/api/loan-applications/pending", headers=auth_headers, json=payload
    )
    return response


def test_pending_creation_and_submission_requires_later_confirmation(client, auth_headers):
    pending_response = _create_pending(client, auth_headers)
    assert pending_response.status_code == 201, pending_response.text
    pending = pending_response.json()
    assert pending["status"] == "AWAITING_CONFIRMATION"
    assert pending["confirmation_reference"].startswith("CONF-...")
    assert float(pending["calculated_emi"]) == pytest.approx(16607.15, abs=0.01)
    token = pending["confirmation_token"]

    refused = client.post(
        "/api/loan-applications/submit",
        headers=auth_headers,
        json={"customer_id": "CUST1001", "confirmation_token": token, "confirmed": False},
    )
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "CONFIRMATION_REQUIRED"

    submitted = client.post(
        "/api/loan-applications/submit",
        headers=auth_headers,
        json={"customer_id": "CUST1001", "confirmation_token": token, "confirmed": True},
    )
    assert submitted.status_code == 201, submitted.text
    result = submitted.json()
    assert result["application_id"].startswith("PL-")
    assert result["status"] == "SUBMITTED"
    assert result["idempotent"] is False
    assert token not in submitted.text

    read_back = client.get(
        f"/api/loan-applications/{result['application_id']}", headers=auth_headers
    )
    assert read_back.status_code == 200
    assert read_back.json()["application_id"] == result["application_id"]

    repeated = client.post(
        "/api/loan-applications/submit",
        headers=auth_headers,
        json={"customer_id": "CUST1001", "confirmation_token": token, "confirmed": True},
    )
    assert repeated.status_code == 200
    assert repeated.json()["idempotent"] is True
    assert repeated.json()["application_id"] == result["application_id"]


def test_pending_creation_rejects_ineligible_customer(client, auth_headers):
    response = _create_pending(
        client, auth_headers, loan_amount="500000", monthly_salary="10000", existing_emi="5000"
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INELIGIBLE"


@pytest.mark.parametrize(
    ("account_status", "kyc_status", "expected_code"),
    [("INACTIVE", "VERIFIED", "ACCOUNT_INACTIVE"), ("ACTIVE", "PENDING", "KYC_NOT_VERIFIED")],
)
def test_pending_creation_requires_active_account_and_verified_kyc(
    client, auth_headers, account_status, kyc_status, expected_code
):
    with client.app.state.session_factory() as db:
        customer = db.get(Customer, "CUST1001")
        customer.account_status = account_status
        customer.kyc_status = kyc_status
        db.commit()
    response = _create_pending(client, auth_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == expected_code


def test_pending_creation_rejects_server_calculation_mismatch(client, auth_headers):
    payload = pending_payload()
    payload["calculated_emi"] = "1"
    response = client.post(
        "/api/loan-applications/pending", headers=auth_headers, json=payload
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TERMS_MISMATCH"


def test_unknown_expired_and_cancelled_tokens_are_rejected(client, auth_headers):
    unknown = client.post(
        "/api/loan-applications/submit",
        headers=auth_headers,
        json={"customer_id": "CUST1001", "confirmation_token": "x" * 32, "confirmed": True},
    )
    assert unknown.status_code == 404

    expired_response = _create_pending(client, auth_headers)
    token = expired_response.json()["confirmation_token"]
    with client.app.state.session_factory() as db:
        pending = db.query(PendingApplication).filter_by(confirmation_token=token).one()
        pending.expires_at = utc_now() - timedelta(minutes=1)
        db.commit()
    expired = client.post(
        "/api/loan-applications/submit",
        headers=auth_headers,
        json={"customer_id": "CUST1001", "confirmation_token": token, "confirmed": True},
    )
    assert expired.status_code == 410

    cancel_response = _create_pending(client, auth_headers)
    cancel_token = cancel_response.json()["confirmation_token"]
    cancelled = client.post(
        f"/api/loan-applications/{cancel_token}/cancel", headers=auth_headers
    )
    assert cancelled.status_code == 200
    blocked = client.post(
        "/api/loan-applications/submit",
        headers=auth_headers,
        json={
            "customer_id": "CUST1001",
            "confirmation_token": cancel_token,
            "confirmed": True,
        },
    )
    assert blocked.status_code == 409


def test_changed_terms_cancel_previous_pending_confirmation(client, auth_headers):
    first = _create_pending(client, auth_headers)
    original_token = first.json()["confirmation_token"]
    changed = _create_pending(client, auth_headers, loan_amount="450000")
    assert changed.status_code == 201
    with client.app.state.session_factory() as db:
        old = db.query(PendingApplication).filter_by(confirmation_token=original_token).one()
        assert old.status == "CANCELLED"
        assert old.cancelled_at is not None
