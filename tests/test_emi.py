from decimal import Decimal

import pytest

from app.services.emi_service import calculate_loan_emi, calculate_monthly_emi


def test_sample_emi_total_payment_and_interest_use_financial_rounding():
    result = calculate_loan_emi(500000, 36, 12)
    assert result["monthly_emi"] == Decimal("16607.15")
    assert result["total_payment"] == Decimal("597857.40")
    assert result["total_interest"] == Decimal("97857.40")
    assert result["currency"] == "INR"
    assert result["rate_type"] == "Mock training rate"


@pytest.mark.parametrize(
    ("principal", "tenure_months", "annual_rate"),
    [
        (0, 36, 12),
        (-1, 36, 12),
        (500000, 0, 12),
        (500000, 36, 0),
        (500000, 36, -1),
    ],
)
def test_invalid_emi_inputs_are_rejected(principal, tenure_months, annual_rate):
    with pytest.raises(ValueError):
        calculate_monthly_emi(principal, annual_rate, tenure_months)
