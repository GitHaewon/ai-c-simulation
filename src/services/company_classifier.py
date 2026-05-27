"""
Company classification layer.
Determines investment type and returns the appropriate simulation parameter template.
Per CLAUDE.md §5: classification logic is deterministic — zero LLM calls.
"""
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CompanyType(str, Enum):
    MEGA_CAP_PUBLIC = "mega_cap_public"
    LARGE_CAP_PUBLIC = "large_cap_public"
    GROWTH_STAGE = "growth_stage"
    STARTUP = "startup"
    PRE_IPO = "pre_ipo"


@dataclass
class SimulationTemplate:
    company_type: CompanyType
    revenue_growth_rate: float
    ebitda_margin: float
    ev_revenue_multiple: float
    holding_period_years: int
    discount_rate: float
    foreign_revenue_pct: float
    valuation_basis: str          # "ebitda_derived" | "revenue" | "arr"
    irr_expected_range: tuple[float, float]
    moic_expected_range: tuple[float, float]
    label_kr: str


# ── Known company name sets ───────────────────────────────────────────────────

_MEGA_CAP_NAMES: set[str] = {
    "삼성전자", "samsung electronics", "samsung",
    "sk하이닉스", "sk hynix", "skhynix",
    "lg전자", "lg electronics",
    "현대차", "현대자동차", "hyundai motor",
    "포스코홀딩스", "포스코", "posco",
    "네이버", "naver",
    "카카오", "kakao",
    "기아", "kia",
    "삼성바이오로직스",
    "셀트리온", "celltrion",
    "kb금융", "신한금융", "하나금융",
    "한국전력", "kepco",
    "sk텔레콤", "skt",
    "kt",
    "현대모비스",
    "lg화학",
    "삼성sdi", "삼성전기",
}

_LARGE_CAP_NAMES: set[str] = {
    "카카오뱅크", "kakaobank",
    "크래프톤", "krafton",
    "하이브", "hybe",
    "엔씨소프트", "ncsoft",
    "넥슨", "nexon",
    "두산에너빌리티",
    "한화에어로스페이스",
    "lg이노텍",
    "sk바이오팜", "한미약품",
    "카카오페이",
    "에코프로비엠", "에코프로",
}

# Deal stage keyword sets
_STARTUP_STAGES: frozenset[str] = frozenset({
    "seed", "pre-seed", "angel", "series a", "시리즈 a", "씨드", "pre-series a",
})
_GROWTH_STAGES: frozenset[str] = frozenset({
    "series b", "series c", "시리즈 b", "시리즈 c", "growth stage", "growth",
})
_PRE_IPO_STAGES: frozenset[str] = frozenset({
    "pre-ipo", "프리 ipo", "late stage", "series d", "series e",
    "시리즈 d", "시리즈 e",
})
_PUBLIC_STAGES: frozenset[str] = frozenset({
    "public", "listed", "상장사", "상장", "유가증권", "kospi", "kosdaq",
})


# ── Simulation parameter templates ───────────────────────────────────────────
#
# Revenue normalization note:
#   For mega/large-cap, revenue_usd_m is set to invested_capital in pipeline.py.
#   MOIC = exit_revenue * multiple / invested_capital
#       = invested * (1+g)^N * multiple / invested
#       = (1+g)^N * multiple
#   This correctly scales returns relative to investment, independent of company size.

_TEMPLATES: dict[CompanyType, SimulationTemplate] = {
    CompanyType.MEGA_CAP_PUBLIC: SimulationTemplate(
        company_type=CompanyType.MEGA_CAP_PUBLIC,
        # 7% CAGR: conservative for mature mega-cap (Samsung 2024-2028 consensus: 5-10%)
        revenue_growth_rate=0.07,
        # 18% EBITDA margin: replaced by DART-derived value when available
        ebitda_margin=0.18,
        # EV/Revenue ≈ EV/EBITDA(8-10x) × margin(15-20%): 1.5x is mid-range
        ev_revenue_multiple=1.50,
        holding_period_years=5,
        # ~9% WACC: investment-grade Korean mega-cap
        discount_rate=0.09,
        # Samsung: ~55% overseas, SK하이닉스: ~90% overseas
        foreign_revenue_pct=0.55,
        valuation_basis="ebitda_derived",
        irr_expected_range=(0.08, 0.25),
        moic_expected_range=(1.2, 4.0),
        label_kr="초대형 상장사 (Mega-cap)",
    ),
    CompanyType.LARGE_CAP_PUBLIC: SimulationTemplate(
        company_type=CompanyType.LARGE_CAP_PUBLIC,
        revenue_growth_rate=0.12,
        ebitda_margin=0.20,
        ev_revenue_multiple=2.50,
        holding_period_years=5,
        discount_rate=0.11,
        foreign_revenue_pct=0.30,
        valuation_basis="ebitda_derived",
        irr_expected_range=(0.12, 0.35),
        moic_expected_range=(1.5, 5.0),
        label_kr="대형 상장사 (Large-cap)",
    ),
    CompanyType.PRE_IPO: SimulationTemplate(
        company_type=CompanyType.PRE_IPO,
        revenue_growth_rate=0.30,
        ebitda_margin=0.12,
        ev_revenue_multiple=5.00,
        holding_period_years=3,
        discount_rate=0.18,
        foreign_revenue_pct=0.20,
        valuation_basis="revenue",
        irr_expected_range=(0.18, 0.45),
        moic_expected_range=(1.5, 6.0),
        label_kr="Pre-IPO (상장 전)",
    ),
    CompanyType.GROWTH_STAGE: SimulationTemplate(
        company_type=CompanyType.GROWTH_STAGE,
        revenue_growth_rate=0.45,
        ebitda_margin=0.10,
        ev_revenue_multiple=7.00,
        holding_period_years=5,
        discount_rate=0.20,
        foreign_revenue_pct=0.20,
        valuation_basis="revenue",
        irr_expected_range=(0.20, 0.50),
        moic_expected_range=(2.0, 8.0),
        label_kr="성장 단계 (Growth-stage)",
    ),
    CompanyType.STARTUP: SimulationTemplate(
        company_type=CompanyType.STARTUP,
        revenue_growth_rate=1.20,
        ebitda_margin=0.05,
        ev_revenue_multiple=10.00,
        holding_period_years=7,
        discount_rate=0.35,
        foreign_revenue_pct=0.10,
        valuation_basis="arr",
        irr_expected_range=(0.25, 0.60),
        moic_expected_range=(3.0, 15.0),
        label_kr="스타트업 (Early-stage)",
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────

def classify_company(
    company_name: str,
    deal_stage: str = "",
    dart_revenue_krw: float | None = None,
) -> CompanyType:
    """
    Classify a company into an investment type.

    Priority order:
    1. Known mega-cap name
    2. Known large-cap name
    3. DART revenue threshold (30조+ → mega, 1조+ → large)
    4. Deal stage keywords (public → large, pre-ipo, growth, startup)
    5. Default: growth stage
    """
    name_lower = company_name.lower().strip()
    stage_lower = (deal_stage or "").lower().strip()

    # 1. Known mega-cap
    for known in _MEGA_CAP_NAMES:
        if known == name_lower or known in name_lower or name_lower in known:
            logger.info("[classifier] '%s' → MEGA_CAP_PUBLIC (이름 매칭: %s)", company_name, known)
            return CompanyType.MEGA_CAP_PUBLIC

    # 2. Known large-cap
    for known in _LARGE_CAP_NAMES:
        if known == name_lower or known in name_lower or name_lower in known:
            logger.info("[classifier] '%s' → LARGE_CAP_PUBLIC (이름 매칭: %s)", company_name, known)
            return CompanyType.LARGE_CAP_PUBLIC

    # 3. DART revenue threshold
    if dart_revenue_krw is not None and dart_revenue_krw > 0:
        if dart_revenue_krw >= 30_000_000_000_000:   # 30조원+
            logger.info(
                "[classifier] '%s' → MEGA_CAP_PUBLIC (DART 매출 %.1f조원)",
                company_name, dart_revenue_krw / 1e12,
            )
            return CompanyType.MEGA_CAP_PUBLIC
        if dart_revenue_krw >= 1_000_000_000_000:    # 1조원+
            logger.info(
                "[classifier] '%s' → LARGE_CAP_PUBLIC (DART 매출 %.1f조원)",
                company_name, dart_revenue_krw / 1e12,
            )
            return CompanyType.LARGE_CAP_PUBLIC

    # 4. Deal stage keywords
    for stage in _PUBLIC_STAGES:
        if stage in stage_lower:
            logger.info("[classifier] '%s' → LARGE_CAP_PUBLIC (투자 단계: %s)", company_name, deal_stage)
            return CompanyType.LARGE_CAP_PUBLIC

    for stage in _STARTUP_STAGES:
        if stage in stage_lower:
            logger.info("[classifier] '%s' → STARTUP (투자 단계: %s)", company_name, deal_stage)
            return CompanyType.STARTUP

    for stage in _PRE_IPO_STAGES:
        if stage in stage_lower:
            logger.info("[classifier] '%s' → PRE_IPO (투자 단계: %s)", company_name, deal_stage)
            return CompanyType.PRE_IPO

    for stage in _GROWTH_STAGES:
        if stage in stage_lower:
            logger.info("[classifier] '%s' → GROWTH_STAGE (투자 단계: %s)", company_name, deal_stage)
            return CompanyType.GROWTH_STAGE

    # 5. Default
    logger.info("[classifier] '%s' → GROWTH_STAGE (기본값)", company_name)
    return CompanyType.GROWTH_STAGE


def get_simulation_template(company_type: CompanyType) -> SimulationTemplate:
    return _TEMPLATES[company_type]
