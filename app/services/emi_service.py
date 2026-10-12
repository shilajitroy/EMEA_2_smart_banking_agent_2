from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
DEFAULT_ANNUAL_INTEREST_RATE = Decimal("12.00")


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal | float | int | str) -> Decimal:
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_monthly_emi(
    principal: Decimal | float | int | str,
    annual_rate: Decimal | float | int | str,
    tenure_months: int,
) -> Decimal:
    amount = to_decimal(principal)
    rate = to_decimal(annual_rate)
    if amount <= 0:
        raise ValueError("Principal must be greater than zero.")
    if rate <= 0:
        raise ValueError("Annual interest rate must be greater than zero.")
    if tenure_months <= 0:
        raise ValueError("Tenure must be greater than zero.")

    monthly_rate = rate / Decimal("1200")
    growth = (Decimal("1") + monthly_rate) ** tenure_months
    emi = amount * monthly_rate * growth / (growth - Decimal("1"))
    return money(emi)


def calculate_loan_emi(
    principal: Decimal | float | int | str,
    tenure_months: int,
    annual_interest_rate: Decimal | float | int | str = DEFAULT_ANNUAL_INTEREST_RATE,
) -> dict[str, object]:
    """Calculate a reducing-balance personal-loan EMI using INR and financial rounding."""
    amount = money(principal)
    rate = to_decimal(annual_interest_rate)
    emi = calculate_monthly_emi(amount, rate, tenure_months)
    total_payment = money(emi * tenure_months)
    return {
        "success": True,
        "principal": amount,
        "tenure_months": tenure_months,
        "annual_interest_rate": rate,
        "monthly_emi": emi,
        "total_payment": total_payment,
        "total_interest": money(total_payment - amount),
        "currency": "INR",
        "rate_type": "Mock training rate" if rate == DEFAULT_ANNUAL_INTEREST_RATE else "Customer-provided rate",
    }


def calculate_total_interest(
    principal: Decimal | float | int | str,
    annual_rate: Decimal | float | int | str,
    tenure_months: int,
) -> Decimal:
    emi = calculate_monthly_emi(principal, annual_rate, tenure_months)
    return money(emi * tenure_months - to_decimal(principal))


def calculate_total_payable(
    principal: Decimal | float | int | str,
    annual_rate: Decimal | float | int | str,
    tenure_months: int,
) -> Decimal:
    emi = calculate_monthly_emi(principal, annual_rate, tenure_months)
    return money(emi * tenure_months)
