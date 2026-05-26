from pydantic import BaseModel, Field


class DealInput(BaseModel):
    company_name: str = Field(..., min_length=1)
    industry: str = Field(..., min_length=1)
    deal_stage: str = ""
    investment_amount_usd_m: float = Field(default=0.0, ge=0.0)
    shock_scenario: str = ""
