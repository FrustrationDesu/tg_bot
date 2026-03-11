from decimal import Decimal

from pydantic import BaseModel, Field


class SpinRequest(BaseModel):
    user_id: int
    external_round_id: str = Field(min_length=3, max_length=64)
    bet_amount: Decimal = Field(gt=0)
    win_amount: Decimal = Field(ge=0)


class SpinResponse(BaseModel):
    user_id: int
    external_round_id: str
    balance: float
