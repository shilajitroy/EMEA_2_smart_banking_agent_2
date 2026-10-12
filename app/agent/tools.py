from __future__ import annotations

from decimal import Decimal
import re
from typing import Annotated
from typing import Any
from urllib.parse import quote

import httpx
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import InjectedState

from app.config import settings
from app.services.emi_service import calculate_loan_emi as calculate_loan_emi_service
from app.services.eligibility_service import verify_loan_eligibility as eligibility_service

REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=3.0)


def _headers() -> dict[str, str]:
    if not settings.banking_api_token:
        raise RuntimeError("BANKING_API_TOKEN is not configured; set it in .env.")
    return {"Authorization": f"Bearer {settings.banking_api_token}"}


def _valid_customer_id(customer_id: str) -> bool:
    return bool(re.fullmatch(r"CUST[A-Z0-9]{4,28}", customer_id.strip(), flags=re.IGNORECASE))


def _api_error(exc: httpx.HTTPStatusError) -> dict[str, object]:
    response = exc.response
    try:
        body = response.json()
        message = body.get("error", {}).get("message", "Banking API request failed.")
    except (ValueError, AttributeError):
        message = "Banking API request failed."
    return {"success": False, "error": str(message), "status_code": response.status_code}


def _request_error(exc: httpx.RequestError) -> dict[str, object]:
    return {
        "success": False,
        "error": (
            "Could not reach the FastAPI service. Start it with "
            "`uvicorn app.main:app --reload` and verify BANKING_API_URL."
        ),
        "error_type": type(exc).__name__,
    }


def _has_explicit_confirmation(messages: list[Any]) -> bool:
    latest_customer_message = next(
        (
            message.content
            for message in reversed(messages)
            if isinstance(message, HumanMessage) and isinstance(message.content, str)
        ),
        "",
    )
    text = latest_customer_message.strip().lower()
    if re.search(r"\b(?:no|cancel|stop|don't|do not|not)\b", text):
        return False
    return bool(
        re.search(r"\b(?:yes|yeah|yep)\b.{0,50}\b(?:submit|proceed|application)\b", text)
        or re.search(r"\bi\s+confirm\b.{0,50}\b(?:submit|proceed|application|it)\b", text)
    )


@tool
def calculate_loan_emi(
    principal: Decimal,
    tenure_months: int,
    annual_interest_rate: Decimal = Decimal("12"),
) -> dict[str, Any]:
    """Calculate the deterministic INR reducing-balance EMI; use 12% as the mock rate if none was provided."""
    try:
        return calculate_loan_emi_service(principal, tenure_months, annual_interest_rate)
    except (ValueError, ArithmeticError) as exc:
        return {"success": False, "error": str(exc)}


@tool
def verify_loan_eligibility(
    loan_amount: Decimal,
    monthly_salary: Decimal,
    existing_monthly_emi: Decimal,
    tenure_months: int,
    annual_interest_rate: Decimal = Decimal("12"),
) -> dict[str, Any]:
    """Check eligibility with a server-calculated EMI derived from the supplied loan terms."""
    try:
        emi = calculate_loan_emi_service(
            loan_amount, tenure_months, annual_interest_rate
        )["monthly_emi"]
        return eligibility_service(
            loan_amount, monthly_salary, existing_monthly_emi, emi
        )
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except (ArithmeticError, KeyError, TypeError):
        return {"success": False, "error": "Could not calculate eligibility from the supplied terms."}


@tool
def retrieve_account_details(customer_id: str) -> dict[str, Any]:
    """Retrieve masked account details, account status, balance, and KYC status from the protected API."""
    if not _valid_customer_id(customer_id):
        return {"success": False, "error": "A valid customer ID is required; do not invent one."}
    url = f"{settings.banking_api_url.rstrip('/')}/api/accounts/{quote(customer_id, safe='')}"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(url, headers=_headers())
            response.raise_for_status()
            return {"success": True, **response.json()}
    except httpx.HTTPStatusError as exc:
        return _api_error(exc)
    except httpx.RequestError as exc:
        return _request_error(exc)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}


@tool
def prepare_loan_application(
    customer_id: str,
    loan_amount: Decimal,
    tenure_months: int,
    annual_interest_rate: Decimal,
    calculated_emi: Decimal,
    monthly_salary: Decimal,
    existing_emi: Decimal,
    foir_percent: Decimal,
    eligible: bool,
) -> dict[str, Any]:
    """Create a server-validated pending loan application that requires later explicit confirmation."""
    if not _valid_customer_id(customer_id):
        return {"success": False, "error": "A valid customer ID is required; do not invent one."}
    if not eligible:
        return {"success": False, "error": "An ineligible loan cannot be prepared for submission."}
    payload = {
        "customer_id": customer_id,
        "loan_amount": str(loan_amount),
        "tenure_months": tenure_months,
        "annual_interest_rate": str(annual_interest_rate),
        "calculated_emi": str(calculated_emi),
        "monthly_salary": str(monthly_salary),
        "existing_emi": str(existing_emi),
        "foir_percent": str(foir_percent),
        "eligible": eligible,
    }
    url = f"{settings.banking_api_url.rstrip('/')}/api/loan-applications/pending"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(url, headers=_headers(), json=payload)
            response.raise_for_status()
            return {"success": True, **response.json()}
    except httpx.HTTPStatusError as exc:
        return _api_error(exc)
    except httpx.RequestError as exc:
        return _request_error(exc)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}


@tool
def submit_loan_application(
    customer_id: str,
    confirmation_token: str,
    confirmed: bool,
    messages: Annotated[list[Any], InjectedState("messages")],
) -> dict[str, Any]:
    """Submit a stored pending application only when the customer explicitly confirms in a later turn."""
    if confirmed is not True or not _has_explicit_confirmation(messages):
        return {
            "success": False,
            "error": "A clear affirmative confirmation in the latest customer message is required.",
        }
    url = f"{settings.banking_api_url.rstrip('/')}/api/loan-applications/submit"
    payload = {
        "customer_id": customer_id,
        "confirmation_token": confirmation_token,
        "confirmed": confirmed,
    }
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(url, headers=_headers(), json=payload)
            response.raise_for_status()
            return {"success": True, **response.json()}
    except httpx.HTTPStatusError as exc:
        return _api_error(exc)
    except httpx.RequestError as exc:
        return _request_error(exc)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
