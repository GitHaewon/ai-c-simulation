"""
End-to-end IC simulation pipeline.
Wires: HybridRetriever → multi-agent debate → Shock Simulation → Memo generation.
"""
import datetime
import logging
from collections.abc import Callable
from dataclasses import dataclass

from src.agents.orchestrator import run_ic_simulation
from src.core.llm.claude_client import ClaudeClient
from src.models.deal import DealInput
from src.models.memo import ICMemo
from src.models.simulation import DealFinancials, SimulationResult
from src.models.state import ICState
from src.services.company_classifier import (
    CompanyType,
    classify_company,
    get_simulation_template,
)
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

        # ── Step 0: DART 공시 데이터 인덱싱 ──────────────────────────────────
        log(f"▶ DART 공시 데이터 확인 중: {deal.company_name} …")
        dart_chunks = self._ensure_dart_indexed(deal.company_name)
        if dart_chunks > 0:
            log(f"  ✓ DART 데이터 인덱싱 완료: {dart_chunks}개 청크")
        elif dart_chunks == 0:
            log("  ℹ DART 데이터: API 키 미설정 또는 기업 미식별")
        else:
            log("  ✓ DART 데이터: 이미 인덱싱됨")

        # ── Step 0b: DART 재무 지표 추출 (시뮬레이션 파라미터 보정용) ────────
        dart_revenue_krw, dart_op_margin = self._extract_dart_key_metrics(deal.company_name)
        if dart_revenue_krw:
            log(
                f"  ✓ DART 재무 추출: 매출 {dart_revenue_krw / 1e12:.1f}조원"
                + (f", 영업이익률 {dart_op_margin * 100:.1f}%" if dart_op_margin is not None else "")
            )

        # ── Step 1: 기업 분류 ─────────────────────────────────────────────────
        company_type = classify_company(deal.company_name, deal.deal_stage, dart_revenue_krw)
        template = get_simulation_template(company_type)
        log(
            f"  ✓ 기업 분류: {template.label_kr} | "
            f"목표 IRR {template.irr_expected_range[0]*100:.0f}–{template.irr_expected_range[1]*100:.0f}%"
            f", MOIC {template.moic_expected_range[0]:.1f}–{template.moic_expected_range[1]:.1f}x"
        )

        # ── Step 2: 멀티 에이전트 IC 심의 ────────────────────────────────────
        log(f"▶ Step 1 / 3 — AI 투자위원회 심의: {deal.company_name} …")
        state = run_ic_simulation(deal, self.client, self.retriever)

        # ── Step 3: 충격 시뮬레이션 ──────────────────────────────────────────
        log("▶ Step 2 / 3 — 충격 시나리오 시뮬레이션 …")
        financials = self._build_financials(deal, dart_revenue_krw, dart_op_margin)
        simulation = run_simulation(financials)

        # ── Step 4: IC 보고서 생성 ────────────────────────────────────────────
        log("▶ Step 3 / 3 — 투자 검토 보고서 생성 …")
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

        log("✓ IC 시뮬레이션 완료.")
        return PipelineResult(state=state, simulation=simulation, memo=memo, deal=deal)

    # ── DART helpers ──────────────────────────────────────────────────────────

    def _ensure_dart_indexed(self, company_name: str) -> int:
        """
        회사별 DART 데이터 자동 인덱싱.
        반환: 새로 인덱싱된 청크 수 / -1(이미 있음) / 0(API 키 없음)
        """
        from src.tools.dart_client import DartClient
        from src.tools.dart_indexer import index_company_dart_data, is_already_indexed

        dart_client = DartClient()

        if is_already_indexed(company_name, self.retriever):
            return -1

        n = index_company_dart_data(company_name, self.retriever, dart_client)
        return n

    def _extract_dart_key_metrics(
        self, company_name: str
    ) -> tuple[float | None, float | None]:
        """
        DART API에서 매출액, 영업이익 추출.
        반환: (revenue_krw, op_margin) — 실패 시 (None, None).
        시뮬레이션 파라미터 보정에만 사용; 실패해도 기본값으로 진행.
        """
        from src.tools.dart_client import DartClient

        dart = DartClient()
        if not dart.is_available:
            return None, None

        corp_code = dart.resolve_corp_code(company_name)
        if not corp_code:
            return None, None

        try:
            # 직전 회계연도 우선, 없으면 그 전년도
            year = str(datetime.date.today().year - 1)
            stmts = dart.get_financial_statements(corp_code, year)
            if not stmts:
                stmts = dart.get_financial_statements(corp_code, str(int(year) - 1))

            revenue_krw: float | None = None
            op_income_krw: float | None = None

            for s in stmts:
                if s.account_nm == "매출액" and s.thstrm_amount:
                    try:
                        revenue_krw = float(s.thstrm_amount.replace(",", ""))
                    except ValueError:
                        pass
                elif s.account_nm == "영업이익" and s.thstrm_amount:
                    try:
                        op_income_krw = float(s.thstrm_amount.replace(",", ""))
                    except ValueError:
                        pass

            op_margin: float | None = None
            if revenue_krw and revenue_krw > 0 and op_income_krw is not None:
                op_margin = op_income_krw / revenue_krw
                logger.info(
                    "DART 재무 추출 완료: '%s' 매출=%.1f조원, 영업이익률=%.1f%%",
                    company_name, revenue_krw / 1e12, op_margin * 100,
                )

            return revenue_krw, op_margin

        except Exception as exc:
            logger.warning("DART 재무 지표 추출 실패 ('%s'): %s", company_name, exc)
            return None, None

    # ── Financials builder ────────────────────────────────────────────────────

    def _build_financials(
        self,
        deal: DealInput,
        dart_revenue_krw: float | None = None,
        dart_op_margin: float | None = None,
    ) -> DealFinancials:
        """
        Company-type-aware financial parameter construction.

        Revenue normalization (mega/large-cap):
          revenue_usd_m = invested_capital_usd_m (normalized to stake size).
          MOIC = (1+g)^N × exit_multiple, independent of absolute company revenue.
          This avoids artificially inflating returns by using the company's $200B revenue.

        Parameter source priority:
          1. DART-derived (op_margin → EBITDA margin)
          2. Classification template defaults
        """
        company_type = classify_company(deal.company_name, deal.deal_stage, dart_revenue_krw)
        template = get_simulation_template(company_type)

        logger.info(
            "[pipeline] 시뮬레이션 파라미터 [%s | %s]: "
            "성장률=%.0f%%, EV/Rev=%.1fx, 할인율=%.0f%%, 보유기간=%d년",
            deal.company_name,
            template.label_kr,
            template.revenue_growth_rate * 100,
            template.ev_revenue_multiple,
            template.discount_rate * 100,
            template.holding_period_years,
        )

        # DART 영업이익률 → EBITDA 마진 보정
        # EBITDA margin ≈ 영업이익률 + ~5% D&A (반도체 등 capex-heavy 기업 기준)
        ebitda_margin = template.ebitda_margin
        if dart_op_margin is not None:
            dart_ebitda = min(max(dart_op_margin + 0.05, 0.03), 0.55)
            logger.info(
                "[pipeline] DART 기반 EBITDA 마진 보정: %.1f%% → %.1f%% (영업이익률 %.1f%%)",
                template.ebitda_margin * 100,
                dart_ebitda * 100,
                dart_op_margin * 100,
            )
            ebitda_margin = dart_ebitda

        invested = max(deal.investment_amount_usd_m, 1.0)

        # 대형 상장사: 투자금액 기준 수익률 정규화
        # 스타트업/성장 단계: 회사 규모 기반 (투자금 50% 수준 초기 매출 가정)
        if company_type in (CompanyType.MEGA_CAP_PUBLIC, CompanyType.LARGE_CAP_PUBLIC):
            revenue_usd_m = invested
        else:
            revenue_usd_m = max(invested * 0.5, 1.0)

        return DealFinancials(
            company_name=deal.company_name,
            invested_capital_usd_m=invested,
            revenue_usd_m=revenue_usd_m,
            revenue_growth_rate=template.revenue_growth_rate,
            ebitda_margin=ebitda_margin,
            ev_revenue_multiple=template.ev_revenue_multiple,
            holding_period_years=template.holding_period_years,
            discount_rate=template.discount_rate,
            debt_usd_m=0.0,
            foreign_revenue_pct=template.foreign_revenue_pct,
            company_type=company_type.value,
            valuation_basis=template.valuation_basis,
        )
