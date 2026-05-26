import logging

from langgraph.graph import END, START, StateGraph

from src.agents.bear import BearAgent
from src.agents.bull import BullAgent
from src.agents.chairman import ChairmanAgent
from src.agents.data_collection import DataCollectionAgent
from src.agents.financial_analysis import FinancialAnalysisAgent
from src.agents.risk import RiskAgent
from src.models.deal import DealInput
from src.models.state import ICState

logger = logging.getLogger(__name__)

# ── Node singletons ───────────────────────────────────────────────────────────

_data_collection = DataCollectionAgent()
_financial = FinancialAnalysisAgent()
_risk = RiskAgent()
_bull = BullAgent()
_bear = BearAgent()
_chairman = ChairmanAgent()


def build_graph() -> StateGraph:
    """
    Construct and compile the IC LangGraph workflow.

    Topology
    --------
    START
      └─► data_collection
               │
         ┌─────┼──────┬──────────┐   ← parallel fan-out
         ▼     ▼      ▼          ▼
      financial risk  bull      bear
         │     │      │          │
         └─────┴──────┴──────────┘   ← fan-in (all must complete)
                      │
                   chairman
                      │
                     END
    """
    workflow = StateGraph(ICState)

    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("data_collection", _data_collection)
    workflow.add_node("financial_analysis", _financial)
    workflow.add_node("risk", _risk)
    workflow.add_node("bull", _bull)
    workflow.add_node("bear", _bear)
    workflow.add_node("chairman", _chairman)

    # ── Edges: sequential entry ───────────────────────────────────────────────
    workflow.add_edge(START, "data_collection")

    # ── Edges: fan-out (parallel execution) ──────────────────────────────────
    for analysis_node in ("financial_analysis", "risk", "bull", "bear"):
        workflow.add_edge("data_collection", analysis_node)

    # ── Edges: fan-in (chairman waits for all four) ───────────────────────────
    for analysis_node in ("financial_analysis", "risk", "bull", "bear"):
        workflow.add_edge(analysis_node, "chairman")

    # ── Exit ──────────────────────────────────────────────────────────────────
    workflow.add_edge("chairman", END)

    return workflow.compile()


def run_ic_simulation(deal: DealInput) -> ICState:
    """Entry point — build graph, inject deal input, return final state."""
    graph = build_graph()

    initial_state: ICState = {
        "company_name": deal.company_name,
        "industry": deal.industry,
        "deal_stage": deal.deal_stage,
        "investment_amount_usd_m": deal.investment_amount_usd_m,
        "shock_scenario": deal.shock_scenario,
        "data_collection_output": None,
        "financial_output": None,
        "risk_output": None,
        "bull_output": None,
        "bear_output": None,
        "chairman_output": None,
        "messages": [],
        "stage_log": [],
        "error_log": [],
    }

    logger.info("IC simulation starting for '%s'", deal.company_name)
    final_state: ICState = graph.invoke(initial_state)
    logger.info(
        "IC simulation complete — decision: %s",
        final_state["chairman_output"].final_decision.value
        if final_state.get("chairman_output")
        else "N/A",
    )
    return final_state
