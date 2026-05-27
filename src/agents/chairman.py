import logging

from src.agents.base import BaseAgent
from src.models.agent_output import ChairmanOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)

QUORUM = 3


class ChairmanAgent(BaseAgent):
    agent_id = "chairman"

    def run(self, state: ICState) -> dict:
        vote_tally = self._collect_votes(state)
        final_decision = self._tally(vote_tally)
        quorum_met = len(vote_tally) >= QUORUM

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
            return "LLM 미연결 — 실제 투자위원장 결의 생성 불가.", []

        summaries = "\n".join(
            f"- {agent}: {vote.value}" for agent, vote in vote_tally.items()
        )
        agent_outputs = self._format_agent_outputs(state)
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## 투표 결과\n"
            f"{summaries}\n\n"
            "## 최종 결정 (의결 엔진)\n"
            f"{decision.value}\n\n"
            "## 위원별 심의 요약\n"
            f"{agent_outputs}\n\n"
            "## Task\n"
            "투자위원장으로서 결의 사유와 조건을 작성하십시오. "
            "명시된 형식의 JSON을 반환하십시오."
        )
        try:
            raw = self._call_structured(user_msg)
            rationale = raw.get("resolution_rationale", "")
            conditions = raw.get("conditions", [])
            return rationale, conditions
        except Exception as exc:
            logger.error("[chairman] LLM 실패: %s", exc)
            return "결의 사유 생성 실패 — 원인을 확인하십시오.", []

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
            ("financial_output", "재무 분석관"),
            ("risk_output", "리스크 심사역"),
            ("bull_output", "강세론 위원"),
            ("bear_output", "약세론 위원"),
        ]:
            out = state.get(key)
            if out:
                parts.append(
                    f"### {label} ({out.vote.value})\n"
                    f"주요 발견: {'; '.join(out.findings[:3])}\n"
                    f"투표 사유: {out.vote_rationale}"
                )
        return "\n\n".join(parts) or "위원 심의 결과 없음."
