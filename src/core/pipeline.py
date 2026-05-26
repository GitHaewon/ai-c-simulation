"""
End-to-end IC simulation pipeline.
Wires: HybridRetriever → multi-agent debate → Shock Simulation → Memo generation.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass

from src.agents.orchestrator import run_ic_simulation
from src.core.llm.claude_client import ClaudeClient
from src.models.deal import DealInput
from src.models.memo import ICMemo
from src.models.simulation import DealFinancials, SimulationResult
from src.models.state import ICState
from src.services.memo_builder import build_memo
from src.services.shock_simulator import run_simulation
from src.tools.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    state: ICState
    simulation: SimulationResult
    memo: ICMemo
    deal: DealInput


class ICPipeline:
    """
    Orchestrates the full IC workflow end-to-end.
    All LLM calls are inside the agent nodes; this class is coordination-only.
    """

    def __init__(self, client: ClaudeClient, retriever: HybridRetriever) -> None:
        self.client = client
        self.retriever = retriever

    @classmethod
    def build(cls) -> "ICPipeline":
        """Factory — loads API key from env, creates default components."""
        client = ClaudeClient()
        retriever = HybridRetriever.build()
        logger.info("ICPipeline built")
        return cls(client, retriever)

    def run(
        self,
        deal: DealInput,
        progress_cb: Callable[[str], None] | None = None,
    ) -> PipelineResult:
        def log(msg: str) -> None:
            logger.info(msg)
            if progress_cb:
                progress_cb(msg)

        log(f"▶ DART 공시 데이터 확인 중: {deal.company_name} …")
        dart_chunks = self._ensure_dart_indexed(deal.company_name)
        if dart_chunks > 0:
            log(f"  ✓ DART 데이터 인덱싱 완료: {dart_chunks}개 청크")
        elif dart_chunks == 0:
            log("  ℹ DART 데이터: 이미 인덱싱됨 또는 API 키 미설정")

        log(f"▶ Step 1 / 3 — Multi-agent IC debate for {deal.company_name} …")
        state = run_ic_simulation(deal, self.client, self.retriever)

        log("▶ Step 2 / 3 — Shock simulation …")
        financials = self._build_financials(deal)
        simulation = run_simulation(financials)

        log("▶ Step 3 / 3 — IC Memo generation …")
        memo = build_memo(
            company_name=deal.company_name,
            industry=deal.industry,
            deal_stage=deal.deal_stage,
            investment_amount_usd_m=deal.investment_amount_usd_m,
            data_collection=state.get("data_collection_output"),
            financial_output=state.get("financial_output"),
            risk_output=state.get("risk_output"),
            bull_output=state.get("bull_output"),
            bear_output=state.get("bear_output"),
            chairman_output=state.get("chairman_output"),
            simulation=simulation,
        )

        log("✓ IC simulation complete.")
        return PipelineResult(state=state, simulation=simulation, memo=memo, deal=deal)

    def _ensure_dart_indexed(self, company_name: str) -> int:
        """
        회사별 DART 데이터가 인덱싱되지 않은 경우 자동 인덱싱.
        DART_API_KEY 없으면 0 반환 (graceful degradation).
        반환: 새로 인덱싱된 청크 수 (이미 있으면 -1, 인덱싱 없으면 0)
        """
        from src.tools.dart_client import DartClient
        from src.tools.dart_indexer import index_company_dart_data, is_already_indexed

        dart_client = DartClient()

        if is_already_indexed(company_name, self.retriever):
            return -1   # 이미 인덱싱됨

        n = index_company_dart_data(company_name, self.retriever, dart_client)
        return n

    @staticmethod
    def _build_financials(deal: DealInput) -> DealFinancials:
        """
        Construct DealFinancials from DealInput.
        Revenue / margin defaults are placeholders — Phase 7 will extract
        actual figures from the Financial Analyst agent's structured output.
        """
        return DealFinancials(
            company_name=deal.company_name,
            invested_capital_usd_m=max(deal.investment_amount_usd_m, 1.0),
            revenue_usd_m=5.0,
            revenue_growth_rate=0.50,
            ebitda_margin=0.15,
            ev_revenue_multiple=8.0,
            holding_period_years=5,
            discount_rate=0.12,
            debt_usd_m=0.0,
            foreign_revenue_pct=0.30,
        )
