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
        query = f"{company} 리스크 규제 경쟁 집중도 엑싯 거버넌스"
        if shock:
            query += f" {shock}"
        context = self._retrieve_context(query)

        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[DART 공시 데이터 없음 — LLM 자체 지식 기반 분석]'}\n\n"
            "## Task\n"
            f"{company} 투자의 모든 중요 리스크를 평가하십시오. "
            + (f"충격 시나리오 '{shock}'의 영향도 반드시 평가하십시오. " if shock else "")
            + "명시된 형식의 JSON을 반환하십시오."
        )

        output = self._llm_or_fallback(user_msg, state)
        return {"risk_output": output, "stage_log": ["risk: done"]}

    def _llm_or_fallback(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "리스크 평가"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "CONDITIONAL")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[risk] LLM 실패: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id,
            section="리스크 평가",
            findings=[f"{state['company_name']} 리스크 평가 — LLM 미연결"],
            concerns=["LLM 연결 후 실제 리스크 분석 가능"],
            vote=Vote.CONDITIONAL,
            vote_rationale="LLM 미연결로 분석 불가.",
            confidence=0.0,
        )
