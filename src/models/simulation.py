from enum import Enum

from pydantic import BaseModel, Field


class ShockType(str, Enum):
    INTEREST_RATE = "interest_rate"
    FX_CHANGE = "fx_change"
    MARKET_DOWNTURN = "market_downturn"


class DealFinancials(BaseModel):
    """Base-case financial inputs for a deal. All calculations start here."""

    company_name: str
    invested_capital_usd_m: float = Field(gt=0)
    revenue_usd_m: float = Field(gt=0)
    revenue_growth_rate: float = Field(description="Annual CAGR, e.g. 0.40 for 40%")
    ebitda_margin: float = Field(description="e.g. 0.20 for 20%")
    ev_revenue_multiple: float = Field(gt=0, description="Exit EV/Revenue multiple")
    holding_period_years: int = Field(ge=1, le=15)
    discount_rate: float = Field(description="WACC, e.g. 0.12 for 12%")
    debt_usd_m: float = Field(default=0.0, ge=0.0)
    foreign_revenue_pct: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Fraction of revenue denominated in foreign currency",
    )
    company_type: str = Field(
        default="growth_stage",
        description="Company classification: mega_cap_public | large_cap_public | growth_stage | startup | pre_ipo",
    )
    valuation_basis: str = Field(
        default="revenue",
        description="Primary valuation method: ebitda_derived | revenue | arr",
    )


class ShockScenario(BaseModel):
    shock_type: ShockType
    label: str
    magnitude: float = Field(
        description=(
            "Rate delta in decimal for INTEREST_RATE (e.g. 0.02 = +200bps); "
            "FX change in decimal for FX_CHANGE (e.g. -0.10 = -10%); "
            "downturn severity in decimal for MARKET_DOWNTURN (e.g. 0.30 = -30% shock)"
        )
    )


class ScenarioMetrics(BaseModel):
    label: str
    irr: float | None = Field(description="Internal Rate of Return")
    moic: float = Field(description="Multiple on Invested Capital")
    exit_value_usd_m: float
    exit_revenue_usd_m: float
    exit_multiple: float
    effective_growth_rate: float
    effective_discount_rate: float
    cash_flows: list[float]


class TornadoBar(BaseModel):
    parameter: str
    low_irr: float | None
    high_irr: float | None
    low_label: str
    high_label: str
    irr_swing: float = Field(description="|high_irr - low_irr|")


class SimulationResult(BaseModel):
    company_name: str
    base_case: ScenarioMetrics
    shocked_scenarios: list[ScenarioMetrics]
    tornado_bars: list[TornadoBar]
