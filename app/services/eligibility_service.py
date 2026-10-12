from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.services.emi_service import money


def verify_loan_eligibility(
    loan_amount: Decimal | float | int | str,
    monthly_salary: Decimal | float | int | str,
    existing_monthly_emi: Decimal | float | int | str,
    proposed_monthly_emi: Decimal | float | int | str,
) -> dict[str, object]:
    """Apply the project's deterministic indicative training eligibility rules."""
    amount = money(loan_amount)
    salary = money(monthly_salary)
    existing_emi = money(existing_monthly_emi)
    proposed_emi = money(proposed_monthly_emi)
    if amount <= 0:
        raise ValueError("Loan amount must be greater than zero.")
    if salary <= 0:
        raise ValueError("Monthly salary must be greater than zero.")
    if existing_emi < 0:
        raise ValueError("Existing EMI cannot be negative.")
    if proposed_emi <= 0:
        raise ValueError("Proposed EMI must be greater than zero.")

    obligation = money(existing_emi + proposed_emi)
    foir_percent = (obligation / salary * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    max_foir = Decimal("50.00")
    max_loan_amount = money(salary * Decimal("20"))
    foir_passed = foir_percent <= max_foir
    amount_rule_passed = amount <= max_loan_amount
    reasons: list[str] = []
    if not foir_passed:
        reasons.append("Total monthly obligation exceeds the maximum FOIR of 50%.")
    if not amount_rule_passed:
        reasons.append("Loan amount exceeds 20 times the monthly salary.")
    if not reasons:
        reasons.append("Passes the mock training affordability rules.")

    return {
        "success": True,
        "eligible": foir_passed and amount_rule_passed,
        "loan_amount": amount,
        "monthly_salary": salary,
        "existing_monthly_emi": existing_emi,
        "proposed_monthly_emi": proposed_emi,
        "total_monthly_obligation": obligation,
        "foir_percent": foir_percent,
        "maximum_allowed_foir_percent": max_foir,
        "maximum_loan_amount": max_loan_amount,
        "foir_passed": foir_passed,
        "amount_rule_passed": amount_rule_passed,
        "reasons": reasons,
        "decision_type": "Indicative mock training decision",
    }
