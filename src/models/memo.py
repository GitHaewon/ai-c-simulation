from datetime import date

from pydantic import BaseModel, Field

from src.models.agent_output import Vote


class MemoHeader(BaseModel):
    company_name: str
    industry: str
    deal_stage: str = ""
    investment_amount_usd_m: float = 0.0
    prepared_date: str = Field(default_factory=lambda: date.today().isoformat())


class OverviewSection(BaseModel):
    key_facts: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)


class FinancialSection(BaseModel):
    base_irr_pct: float | None = None
    base_moic: float = 0.0
    exit_value_usd_m: float = 0.0
    exit_multiple: float = 0.0
    findings: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    agent_confidence: float = 0.0


class ThesisSection(BaseModel):
    lead_thesis: str = ""
    bull_points: list[str] = Field(default_factory=list)
    bear_points: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    label: str
    description: str
    severity: str = "Medium"  # Low | Medium | High


class RiskSection(BaseModel):
    risks: list[RiskItem] = Field(default_factory=list)
    agent_confidence: float = 0.0


class ShockSummaryRow(BaseModel):
    label: str
    irr_pct: float | None
    moic: float
    delta_irr_pp: float | None  # vs base case


class ShockSection(BaseModel):
    base_irr_pct: float | None = None
    base_moic: float = 0.0
    scenarios: list[ShockSummaryRow] = Field(default_factory=list)
    top_driver: str = ""
    top_driver_swing_pp: float = 0.0


class RecommendationSection(BaseModel):
    decision: Vote
    vote_tally: dict[str, str] = Field(default_factory=dict)
    quorum_met: bool = False
    conditions: list[str] = Field(default_factory=list)
    rationale: str = ""


class ICMemo(BaseModel):
    header: MemoHeader
    overview: OverviewSection
    financials: FinancialSection
    thesis: ThesisSection
    risks: RiskSection
    shock_summary: ShockSection
    recommendation: RecommendationSection
