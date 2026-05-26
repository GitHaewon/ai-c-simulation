import operator
from typing import Annotated

from langgraph.graph import MessagesState

from src.models.agent_output import (
    AgentOutput,
    ChairmanOutput,
    DataCollectionOutput,
)


class ICState(MessagesState):
    """Shared state that flows through every node in the IC graph."""

    # ── Deal input ────────────────────────────────────────────────────────────
    company_name: str
    industry: str
    deal_stage: str
    investment_amount_usd_m: float
    shock_scenario: str

    # ── Agent outputs (None until the respective node runs) ───────────────────
    data_collection_output: DataCollectionOutput | None
    financial_output: AgentOutput | None
    risk_output: AgentOutput | None
    bull_output: AgentOutput | None
    bear_output: AgentOutput | None
    chairman_output: ChairmanOutput | None

    # ── Audit trail (lists accumulate across parallel writes) ─────────────────
    stage_log: Annotated[list[str], operator.add]
    error_log: Annotated[list[str], operator.add]
