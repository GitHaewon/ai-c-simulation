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


def build_graph(client=None, retriever=None) -> object:
    """
    Build and compile the IC LangGraph workflow.
    Pass ClaudeClient and HybridRetriever to enable real LLM + RAG execution.

    Topology: START → data_collection → [financial, risk, bull, bear] (parallel) → chairman → END
    """
    workflow = StateGraph(ICState)

    workflow.add_node("data_collection",  DataCollectionAgent(client, retriever))
    workflow.add_node("financial_analysis", FinancialAnalysisAgent(client, retriever))
    workflow.add_node("risk",  RiskAgent(client, retriever))
    workflow.add_node("bull",  BullAgent(client, retriever))
    workflow.add_node("bear",  BearAgent(client, retriever))
    workflow.add_node("chairman", ChairmanAgent(client, retriever))

    workflow.add_edge(START, "data_collection")
    for node in ("financial_analysis", "risk", "bull", "bear"):
        workflow.add_edge("data_collection", node)
        workflow.add_edge(node, "chairman")
    workflow.add_edge("chairman", END)

    return workflow.compile()


def run_ic_simulation(
    deal: DealInput,
    client=None,
    retriever=None,
) -> ICState:
    """Entry point — build graph, inject deal, return final state."""
    graph = build_graph(client, retriever)

    initial: ICState = {
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
    final: ICState = graph.invoke(initial)
    decision = final["chairman_output"].final_decision.value if final.get("chairman_output") else "N/A"
    logger.info("IC simulation complete — decision: %s", decision)
    return final
