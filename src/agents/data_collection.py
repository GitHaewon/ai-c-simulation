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
            f"{company} {industry} 매출 재무 시장 경쟁 사업"
        )

        user_msg = (
            "## Deal Summary\n"
            f"{self._build_deal_summary(state)}\n\n"
            "## Retrieved Context\n"
            f"{context or '[DART 공시 데이터 없음 — LLM 자체 지식 기반 분석]'}\n\n"
            "## Task\n"
            f"{company}에 대한 핵심 사실을 수집·정리하십시오. "
            "명시된 형식의 JSON을 반환하십시오."
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
                logger.error("[data_collection] LLM 실패: %s", exc)
                output = self._fallback(state)
        else:
            output = self._fallback(state)

        return {"data_collection_output": output, "stage_log": ["data_collection: done"]}

    @staticmethod
    def _fallback(state: ICState) -> DataCollectionOutput:
        return DataCollectionOutput(
            company_name=state["company_name"],
            industry=state["industry"],
            key_facts=[
                f"{state['company_name']} — {state['industry']} 업종",
                f"투자 단계: {state.get('deal_stage', 'N/A')}",
                f"투자 규모: ${state.get('investment_amount_usd_m', 0):.1f}M",
            ],
            data_sources=["LLM 미연결 — DART 공시 데이터 직접 확인 필요"],
        )
