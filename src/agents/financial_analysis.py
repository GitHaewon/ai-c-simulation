import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class FinancialAnalysisAgent(BaseAgent):
    agent_id = "financial_analysis"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        context = self._retrieve_context(
            f"{company} revenue gross margin EBITDA valuation IRR MOIC financials"
        )
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[No documents indexed yet]'}\n\n"
            "## Task\n"
            f"Perform a financial analysis of {company}. "
            "Return JSON as specified in your instructions."
        )

        output = self._llm_or_placeholder(user_msg, state)
        return {"financial_output": output, "stage_log": ["financial_analysis: done"]}

    def _llm_or_placeholder(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "Financial Analysis"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "CONDITIONAL")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[financial_analysis] LLM failed: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id,
            section="Financial Analysis",
            findings=[f"[placeholder] Financial analysis for {state['company_name']}"],
            concerns=["[placeholder] Connect LLM to enable real analysis"],
            vote=Vote.CONDITIONAL,
            vote_rationale="[placeholder] LLM not connected.",
            confidence=0.0,
        )
