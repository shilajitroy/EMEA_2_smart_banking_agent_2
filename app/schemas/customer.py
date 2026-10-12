from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    customer_name: str
    account_number_masked: str
    account_type: str
    account_status: str
    balance: Decimal
    kyc_status: str
