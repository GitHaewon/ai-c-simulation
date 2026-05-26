import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class RiskAgent(BaseAgent):
    agent_id = "risk"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        shock = state.get("shock_scenario", "")
        query = f"{company} risks regulatory customer concentration key-person exit"
        if shock:
            query += f" {shock}"
        context = self._retrieve_context(query)

        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[No documents indexed yet]'}\n\n"
            "## Task\n"
            f"Assess all material risks for investing in {company}. "
            + (f"The committee has defined a shock scenario: {shock}. Evaluate its impact.\n" if shock else "")
            + "Return JSON as specified in your instructions."
        )

        output = self._llm_or_placeholder(user_msg, state)
        return {"risk_output": output, "stage_log": ["risk: done"]}

    def _llm_or_placeholder(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "Risk Assessment"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "CONDITIONAL")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[risk] LLM failed: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id, section="Risk Assessment",
            findings=[f"[placeholder] Risk assessment for {state['company_name']}"],
            concerns=["[placeholder] Connect LLM to enable real analysis"],
            vote=Vote.CONDITIONAL, vote_rationale="[placeholder]", confidence=0.0,
        )
