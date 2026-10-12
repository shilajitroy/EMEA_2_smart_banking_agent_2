from decimal import Decimal

import pytest

from app.services.eligibility_service import verify_loan_eligibility


def test_sample_eligibility_passes_with_expected_foir():
    result = verify_loan_eligibility(500000, 60000, 5000, 16607.15)
    assert result["eligible"] is True
    assert result["total_monthly_obligation"] == Decimal("21607.15")
    assert result["foir_percent"] == Decimal("36.01")
    assert result["decision_type"] == "Indicative mock training decision"


def test_foir_above_fifty_percent_is_rejected():
    result = verify_loan_eligibility(500000, 60000, 15000, 16607.15)
    assert result["eligible"] is False
    assert result["foir_percent"] > Decimal("50")
    assert result["foir_passed"] is False


def test_loan_amount_above_salary_multiple_is_rejected():
    result = verify_loan_eligibility(1200001, 60000, 0, 1000)
    assert result["eligible"] is False
    assert result["amount_rule_passed"] is False


@pytest.mark.parametrize(
    ("loan_amount", "salary", "existing_emi", "proposed_emi"),
    [(0, 10000, 0, 1000), (10000, 0, 0, 1000), (10000, 10000, -1, 1000), (10000, 10000, 0, 0)],
)
def test_invalid_eligibility_inputs_are_rejected(loan_amount, salary, existing_emi, proposed_emi):
    with pytest.raises(ValueError):
        verify_loan_eligibility(loan_amount, salary, existing_emi, proposed_emi)
