import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path

from src.models.state import ICState

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "src" / "prompts"
_MAX_CONTEXT_CHARS = 6000  # ~2 000 tokens


class BaseAgent(ABC):
    """Common interface for all IC agent nodes."""

    agent_id: str

    def __init__(self, client=None, retriever=None) -> None:
        self._client = client
        self._retriever = retriever
        self._system_prompt = self._load_system_prompt()

    # ── LangGraph callable ────────────────────────────────────────────────────

    def __call__(self, state: ICState) -> dict:
        self._current_company: str = state.get("company_name", "")
        company_type = self._get_company_type(state)
        logger.info(
            "[%s] 시작 (기업='%s', 분류='%s')",
            self.agent_id, self._current_company, company_type,
        )
        try:
            result = self.run(state)
            logger.info("[%s] 완료", self.agent_id)
            return result
        except Exception as exc:
            logger.error("[%s] 실패: %s", self.agent_id, exc)
            return {"error_log": [f"{self.agent_id}: {exc}"]}

    @abstractmethod
    def run(self, state: ICState) -> dict:
        """Execute agent logic and return a partial state update dict."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        path = _PROMPTS_DIR / f"{self.agent_id}_system.txt"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        logger.warning("[%s] 시스템 프롬프트 없음: %s", self.agent_id, path)
        return f"당신은 투자위원회의 {self.agent_id} 역할입니다."

    def _retrieve_context(self, query: str, metadata_filter: dict | None = None) -> str:
        if self._retriever is None:
            return ""
        from src.tools.hybrid_retriever import HybridRetriever

        # Entity match filter: 현재 기업 청크만 검색
        company = getattr(self, "_current_company", "")
        if company:
            entity_filter: dict = {"company_name": company}
            if metadata_filter:
                entity_filter.update(metadata_filter)
            metadata_filter = entity_filter

        result = self._retriever.retrieve(query, top_k=5, metadata_filter=metadata_filter)

        if not result.chunks:
            logger.warning(
                "[%s] RAG 컨텍스트 없음 (기업='%s') — LLM 자체 지식 기반 분석",
                self.agent_id, company,
            )
            return ""

        # 검색 결과 소스 로깅
        sources = [c.chunk.metadata.source_document for c in result.chunks]
        scores = [c.score for c in result.chunks]
        logger.info(
            "[%s] 검색 완료: %d개 청크 | 소스: %s | 점수: %s",
            self.agent_id,
            len(result.chunks),
            sources,
            [f"{s:.4f}" for s in scores],
        )

        raw = HybridRetriever.format_context_with_citations(result)
        return raw[:_MAX_CONTEXT_CHARS] if len(raw) > _MAX_CONTEXT_CHARS else raw

    def _get_company_type(self, state: ICState) -> str:
        """기업 분류 결과 반환 (로깅 및 deal summary용)."""
        from src.services.company_classifier import classify_company, get_simulation_template
        ct = classify_company(state.get("company_name", ""), state.get("deal_stage", ""))
        return get_simulation_template(ct).label_kr

    def _build_deal_summary(self, state: ICState) -> str:
        from src.services.company_classifier import classify_company, get_simulation_template
        company_type = classify_company(
            state.get("company_name", ""),
            state.get("deal_stage", ""),
        )
        tmpl = get_simulation_template(company_type)

        return (
            f"기업명: {state['company_name']}\n"
            f"산업: {state['industry']}\n"
            f"투자 단계: {state.get('deal_stage') or 'N/A'}\n"
            f"투자 규모: ${state.get('investment_amount_usd_m', 0):.1f}M\n"
            f"충격 시나리오: {state.get('shock_scenario') or '없음'}\n"
            f"\n[기업 분류]\n"
            f"유형: {tmpl.label_kr}\n"
            f"밸류에이션 방식: {tmpl.valuation_basis}\n"
            f"적정 IRR 범위: {tmpl.irr_expected_range[0]*100:.0f}–{tmpl.irr_expected_range[1]*100:.0f}%\n"
            f"적정 MOIC 범위: {tmpl.moic_expected_range[0]:.1f}–{tmpl.moic_expected_range[1]:.1f}x"
        )

    def _call_structured(self, user_message: str) -> dict:
        from src.core.llm.claude_client import ClaudeRequest, STRUCTURED_OUTPUT_TEMPERATURE
        request = ClaudeRequest(
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=STRUCTURED_OUTPUT_TEMPERATURE,
            max_tokens=2048,
        )
        response = self._client.complete(request)
        return self._parse_json(response.content)

    def _parse_json(self, text: str) -> dict:
        # Strategy 1: JSON inside markdown code block
        match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if match:
            return json.loads(match.group(1))
        # Strategy 2: first complete top-level JSON object
        depth = 0
        start: int | None = None
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        start = None
        raise ValueError(f"LLM 응답에서 JSON 파싱 실패 (앞 300자): {text[:300]}")
