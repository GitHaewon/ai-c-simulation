import logging

from src.agents.base import BaseAgent
from src.models.agent_output import ChairmanOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)

QUORUM = 3

_VOTE_COLOR = {Vote.APPROVE: "green", Vote.REJECT: "red", Vote.CONDITIONAL: "orange"}


class ChairmanAgent(BaseAgent):
    agent_id = "chairman"

    def run(self, state: ICState) -> dict:
        vote_tally = self._collect_votes(state)
        final_decision = self._tally(vote_tally)
        quorum_met = len(vote_tally) >= QUORUM

        # LLM writes rationale + conditions; tallying stays deterministic.
        rationale, conditions = self._generate_rationale(state, vote_tally, final_decision)

        output = ChairmanOutput(
            final_decision=final_decision,
            vote_tally={k: v.value for k, v in vote_tally.items()},
            quorum_met=quorum_met,
            resolution_rationale=rationale,
            conditions=conditions,
        )
        return {"chairman_output": output, "stage_log": [f"chairman: {final_decision.value}"]}

    # ── LLM rationale ─────────────────────────────────────────────────────────

    def _generate_rationale(
        self, state: ICState, vote_tally: dict[str, Vote], decision: Vote
    ) -> tuple[str, list[str]]:
        if not self._client:
            return "[placeholder] Connect LLM to generate rationale.", []

        summaries = "\n".join(
            f"- {agent}: {vote.value}" for agent, vote in vote_tally.items()
        )
        agent_outputs = self._format_agent_outputs(state)
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Vote Tally\n"
            f"{summaries}\n\n"
            "## Final Decision (from voting engine)\n"
            f"{decision.value}\n\n"
            "## Agent Deliberation Summaries\n"
            f"{agent_outputs}\n\n"
            "## Task\n"
            "Write the chairman's resolution rationale and list any conditions. "
            "Return JSON as specified in your instructions."
        )
        try:
            raw = self._call_structured(user_msg)
            rationale = raw.get("resolution_rationale", "")
            conditions = raw.get("conditions", [])
            return rationale, conditions
        except Exception as exc:
            logger.error("[chairman] LLM failed: %s", exc)
            return "[placeholder] LLM call failed.", []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_votes(state: ICState) -> dict[str, Vote]:
        mapping = {
            "financial_analysis": state.get("financial_output"),
            "risk": state.get("risk_output"),
            "bull": state.get("bull_output"),
            "bear": state.get("bear_output"),
        }
        return {k: v.vote for k, v in mapping.items() if v is not None}

    @staticmethod
    def _tally(votes: dict[str, Vote]) -> Vote:
        counts = {v: 0 for v in Vote}
        for v in votes.values():
            counts[v] += 1
        if counts[Vote.APPROVE] > counts[Vote.REJECT]:
            return Vote.APPROVE
        if counts[Vote.REJECT] > counts[Vote.APPROVE]:
            return Vote.REJECT
        return Vote.CONDITIONAL

    @staticmethod
    def _format_agent_outputs(state: ICState) -> str:
        parts: list[str] = []
        for key, label in [
            ("financial_output", "Financial Analyst"),
            ("risk_output", "Risk Officer"),
            ("bull_output", "Bull Advocate"),
            ("bear_output", "Bear Advocate"),
        ]:
            out = state.get(key)
            if out:
                parts.append(
                    f"### {label} ({out.vote.value})\n"
                    f"Findings: {'; '.join(out.findings[:3])}\n"
                    f"Rationale: {out.vote_rationale}"
                )
        return "\n\n".join(parts) or "No agent outputs available."
