import logging

from src.agents.base import BaseAgent
from src.models.agent_output import DataCollectionOutput
from src.models.state import ICState

logger = logging.getLogger(__name__)


class DataCollectionAgent(BaseAgent):
    agent_id = "data_collection"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        industry = state["industry"]

        context = self._retrieve_context(
            f"{company} {industry} revenue financials market competitive"
        )

        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[No documents indexed yet]'}\n\n"
            "## Task\n"
            f"Collect and structure the key facts about {company}. "
            "Return JSON as specified in your instructions."
        )

        if self._client:
            try:
                raw = self._call_structured(user_msg)
                output = DataCollectionOutput(
                    company_name=company,
                    industry=industry,
                    key_facts=raw.get("key_facts", []),
                    data_sources=raw.get("data_sources", []),
                )
            except Exception as exc:
                logger.error("[data_collection] LLM failed: %s", exc)
                output = self._placeholder(state)
        else:
            output = self._placeholder(state)

        return {"data_collection_output": output, "stage_log": ["data_collection: done"]}

    @staticmethod
    def _placeholder(state: ICState) -> DataCollectionOutput:
        return DataCollectionOutput(
            company_name=state["company_name"],
            industry=state["industry"],
            key_facts=[
                f"[placeholder] {state['company_name']} operates in {state['industry']}",
                f"[placeholder] Deal stage: {state.get('deal_stage', 'N/A')}",
                f"[placeholder] Investment: ${state.get('investment_amount_usd_m', 0):.1f}M",
            ],
            data_sources=["[placeholder] — connect LLM to enable real data collection"],
        )
