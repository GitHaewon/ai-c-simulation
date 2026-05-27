import logging

from src.agents.base import BaseAgent
from src.models.agent_output import AgentOutput, Vote
from src.models.state import ICState

logger = logging.getLogger(__name__)


class BullAgent(BaseAgent):
    agent_id = "bull"

    def run(self, state: ICState) -> dict:
        company = state["company_name"]
        industry = state["industry"]
        context = self._retrieve_context(
            f"{company} {industry} 성장 기회 경쟁우위 시장점유율 기술력"
        )
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[DART 공시 데이터 없음 — LLM 자체 지식 기반 분석]'}\n\n"
            "## Task\n"
            f"{company} 투자에 대한 가장 강력한 강세 논거를 구성하십시오. "
            "기업 분류에 맞는 투자 논리를 적용하십시오. "
            "명시된 형식의 JSON을 반환하십시오."
        )

        output = self._llm_or_fallback(user_msg, state)
        return {"bull_output": output, "stage_log": ["bull: done"]}

    def _llm_or_fallback(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "강세 논거"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "APPROVE")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[bull] LLM 실패: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id,
            section="강세 논거",
            findings=[f"{state['company_name']} 강세 논거 — LLM 미연결"],
            concerns=[],
            vote=Vote.APPROVE,
            vote_rationale="LLM 미연결로 분석 불가.",
            confidence=0.0,
        )
