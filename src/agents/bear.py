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
            f"{company} {industry} 경쟁 리스크 밸류에이션 우려 취약점"
        )
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[DART 공시 데이터 없음 — LLM 자체 지식 기반 분석]'}\n\n"
            "## Task\n"
            f"{company} 투자에 대한 가장 강력한 약세 반론을 구성하십시오. "
            "기업 분류에 맞는 밸류에이션 리스크와 구조적 취약점을 지적하십시오. "
            "명시된 형식의 JSON을 반환하십시오."
        )

        output = self._llm_or_fallback(user_msg, state)
        return {"bear_output": output, "stage_log": ["bear: done"]}

    def _llm_or_fallback(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "약세 논거"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "REJECT")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[bear] LLM 실패: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id,
            section="약세 논거",
            findings=[f"{state['company_name']} 약세 논거 — LLM 미연결"],
            concerns=["LLM 연결 후 실제 분석 가능"],
            vote=Vote.REJECT,
            vote_rationale="LLM 미연결로 분석 불가.",
            confidence=0.0,
        )
