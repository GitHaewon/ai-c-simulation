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
        # Imports deferred to avoid circular imports at module load time.
        self._client = client    # ClaudeClient | None
        self._retriever = retriever  # HybridRetriever | None
        self._system_prompt = self._load_system_prompt()

    # ── LangGraph callable ────────────────────────────────────────────────────

    def __call__(self, state: ICState) -> dict:
        # Cache company name so _retrieve_context can apply entity filter.
        self._current_company: str = state.get("company_name", "")
        logger.info("[%s] starting (company='%s')", self.agent_id, self._current_company)
        try:
            result = self.run(state)
            logger.info("[%s] complete", self.agent_id)
            return result
        except Exception as exc:
            logger.error("[%s] failed: %s", self.agent_id, exc)
            return {"error_log": [f"{self.agent_id}: {exc}"]}

    @abstractmethod
    def run(self, state: ICState) -> dict:
        """Execute agent logic and return a partial state update dict."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        path = _PROMPTS_DIR / f"{self.agent_id}_system.txt"
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        logger.warning("[%s] system prompt not found at %s", self.agent_id, path)
        return f"You are the {self.agent_id} agent on an Investment Committee."

    def _retrieve_context(self, query: str, metadata_filter: dict | None = None) -> str:
        if self._retriever is None:
            return ""
        from src.tools.hybrid_retriever import HybridRetriever

        # Entity match filter: only retrieve chunks for the current company.
        company = getattr(self, "_current_company", "")
        if company:
            entity_filter: dict = {"company_name": company}
            if metadata_filter:
                # Merge — company filter takes priority.
                entity_filter.update(metadata_filter)
            metadata_filter = entity_filter
            logger.debug("[%s] retrieve with entity filter: company='%s'", self.agent_id, company)

        result = self._retriever.retrieve(query, top_k=5, metadata_filter=metadata_filter)

        if not result.chunks:
            logger.warning(
                "[%s] No chunks found for company='%s' — RAG context empty",
                self.agent_id, company,
            )
            return ""

        raw = HybridRetriever.format_context_with_citations(result)
        return raw[:_MAX_CONTEXT_CHARS] if len(raw) > _MAX_CONTEXT_CHARS else raw

    def _build_deal_summary(self, state: ICState) -> str:
        return (
            f"Company: {state['company_name']}\n"
            f"Industry: {state['industry']}\n"
            f"Deal Stage: {state.get('deal_stage') or 'N/A'}\n"
            f"Investment Amount: ${state.get('investment_amount_usd_m', 0):.1f}M\n"
            f"Shock Scenario: {state.get('shock_scenario') or 'None defined'}"
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
        raise ValueError(f"No valid JSON in LLM response (first 300 chars): {text[:300]}")
