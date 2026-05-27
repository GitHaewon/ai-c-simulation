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
            f"{company} 매출액 영업이익 EBITDA 재무제표 밸류에이션 수익성"
        )
        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[DART 공시 데이터 없음 — LLM 자체 지식 기반 분석]'}\n\n"
            "## Task\n"
            f"{company}의 재무 분석을 수행하십시오. "
            "기업 분류(Deal Summary의 [기업 분류] 참조)에 맞는 밸류에이션 지표와 수익률 범위를 적용하십시오. "
            "명시된 형식의 JSON을 반환하십시오."
        )

        output = self._llm_or_fallback(user_msg, state)
        return {"financial_output": output, "stage_log": ["financial_analysis: done"]}

    def _llm_or_fallback(self, user_msg: str, state: ICState) -> AgentOutput:
        if self._client:
            try:
                raw = self._call_structured(user_msg)
                return AgentOutput(
                    agent_id=self.agent_id,
                    section=raw.get("section", "재무 분석"),
                    findings=raw.get("findings", []),
                    concerns=raw.get("concerns", []),
                    vote=Vote(raw.get("vote", "CONDITIONAL")),
                    vote_rationale=raw.get("vote_rationale", ""),
                    confidence=float(raw.get("confidence", 0.5)),
                )
            except Exception as exc:
                logger.error("[financial_analysis] LLM 실패: %s", exc)
        return AgentOutput(
            agent_id=self.agent_id,
            section="재무 분석",
            findings=[f"{state['company_name']} 재무 분석 — LLM 미연결"],
            concerns=["LLM 연결 후 실제 분석 가능"],
            vote=Vote.CONDITIONAL,
            vote_rationale="LLM 미연결로 분석 불가.",
            confidence=0.0,
        )
