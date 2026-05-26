import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class BearAgent(BaseAgent):
    agent_id = "bear"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        industry = state["industry"]
        context = self._retrieve_context(
            f"{company} {industry} competition risk valuation concern weakness threat"
        )
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[No documents indexed yet]'}\n\n"
            "## Task\n"
            f"Build the strongest possible counter-thesis against investing in {company}. "
            "Return JSON as specified in your instructions."
        )

        output = self._llm_or_placeholder(user_msg, state)
        return {"bear_output": output, "stage_log": ["bear: done"]}

    def _llm_or_placeholder(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "Bear Case"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "REJECT")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[bear] LLM failed: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id, section="Bear Case",
            findings=[f"[placeholder] Bear case for {state['company_name']}"],
            concerns=["[placeholder] Connect LLM to enable real analysis"],
            vote=Vote.REJECT, vote_rationale="[placeholder]", confidence=0.0,
        )
