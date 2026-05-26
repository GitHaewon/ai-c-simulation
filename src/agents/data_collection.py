import logging

from src.agents.base import BaseAgent
from src.models.agent_output import DataCollectionOutput
from src.models.state import ICState

logger = logging.getLogger(__name__)


class DataCollectionAgent(BaseAgent):
    """
    First node in the graph.
    Gathers publicly available data about the deal before analysis agents run.
    Placeholder — LLM + RAG retrieval wired in Phase 4.
    """

    agent_id = "data_collection"

    def run(self, state: ICState) -> dict:
        output = DataCollectionOutput(
            company_name=state["company_name"],
            industry=state["industry"],
            key_facts=[
                f"[placeholder] {state['company_name']} operates in {state['industry']}",
                f"[placeholder] Deal stage: {state.get('deal_stage', 'N/A')}",
                f"[placeholder] Investment: ${state.get('investment_amount_usd_m', 0):.1f}M",
            ],
            data_sources=["[placeholder] web search", "[placeholder] RAG retrieval"],
        )
        return {
            "data_collection_output": output,
            "stage_log": ["data_collection: done"],
        }
