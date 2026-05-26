"""
DART 데이터를 HybridRetriever에 인덱싱.
company_name 메타데이터 태깅으로 엔티티 mismatch 방지.
"""
import logging
from datetime import datetime, timedelta

from src.models.retrieval import ChunkMetadata
from src.tools.dart_client import DartClient, DartCompanyInfo, DartFinancialItem

logger = logging.getLogger(__name__)


def is_already_indexed(company_name: str, retriever) -> bool:
    """ChromaDB에 해당 회사 데이터가 이미 인덱싱되어 있는지 확인."""
    try:
        result = retriever._vector_store._collection.get(
            where={"company_name": {"$eq": company_name}},
            limit=1,
            include=[],
        )
        return len(result.get("ids", [])) > 0
    except Exception as exc:
        logger.warning("ChromaDB 인덱싱 확인 실패: %s", exc)
        return False


def index_company_dart_data(
    company_name: str,
    retriever,
    dart_client: DartClient,
    years: list[str] | None = None,
    force: bool = False,
) -> int:
    """
    DART에서 회사 공시 데이터를 가져와 HybridRetriever에 인덱싱.

    company_name 메타데이터로 태깅 → 다른 기업 청크와 완전 분리.
    반환: 인덱싱된 청크 수 (0이면 데이터 없음 또는 이미 인덱싱됨)

    force=True이면 중복 확인 없이 재인덱싱.
    """
    if not force and is_already_indexed(company_name, retriever):
        logger.info("[DartIndexer] '%s' 이미 인덱싱됨 — 건너뜀", company_name)
        return 0

    if not dart_client.is_available:
        logger.warning(
            "[DartIndexer] DART_API_KEY 미설정 — '%s' 실시간 공시 데이터 인덱싱 불가. "
            ".env에 DART_API_KEY를 설정하세요. (https://opendart.fss.or.kr)",
            company_name,
        )
        return 0

    corp_code = dart_client.resolve_corp_code(company_name)
    if not corp_code:
        logger.warning("[DartIndexer] '%s' DART corp_code 없음", company_name)
        return 0

    if years is None:
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 2, current_year + 1)]

    total = 0

    # ── 1. 기업 기본 정보 ─────────────────────────────────────────────────────
    info = dart_client.get_company_info(corp_code)
    if info:
        text = _fmt_company_info(info)
        meta = ChunkMetadata(
            source_document=f"DART_{company_name}_기업정보.txt",
            section="기업 기본 정보",
            date=info.est_dt or "",
            deal_id=company_name,
            company_name=company_name,
        )
        chunks = retriever.index_text(text, meta)
        total += len(chunks)
        logger.info("[DartIndexer] '%s' 기업정보 → %d 청크", company_name, len(chunks))

    # ── 2. 재무제표 (연결 기준, 연도별) ─────────────────────────────────────
    for year in years:
        stmts = dart_client.get_financial_statements(corp_code, year)
        if not stmts:
            logger.debug("[DartIndexer] '%s' %s년 재무제표 없음", company_name, year)
            continue
        text = _fmt_financial_statements(stmts, company_name, year)
        meta = ChunkMetadata(
            source_document=f"DART_{company_name}_재무제표_{year}.txt",
            section=f"연결 재무제표 ({year}년)",
            date=f"{year}-12-31",
            deal_id=company_name,
            company_name=company_name,
        )
        chunks = retriever.index_text(text, meta)
        total += len(chunks)
        logger.info(
            "[DartIndexer] '%s' %s년 재무제표 → %d 청크 (%d 계정)",
            company_name, year, len(chunks), len(stmts),
        )

    # ── 3. 최근 공시 목록 (1년) ──────────────────────────────────────────────
    today = datetime.now()
    start_dt = (today - timedelta(days=365)).strftime("%Y%m%d")
    end_dt = today.strftime("%Y%m%d")
    disclosures = dart_client.get_disclosure_list(corp_code, start_dt, end_dt)
    if disclosures:
        text = _fmt_disclosures(disclosures, company_name)
        meta = ChunkMetadata(
            source_document=f"DART_{company_name}_공시목록.txt",
            section="최근 공시 목록 (1년)",
            date=end_dt,
            deal_id=company_name,
            company_name=company_name,
        )
        chunks = retriever.index_text(text, meta)
        total += len(chunks)
        logger.info(
            "[DartIndexer] '%s' 공시목록 → %d 청크 (%d 건)",
            company_name, len(chunks), len(disclosures),
        )

    logger.info("[DartIndexer] '%s' 인덱싱 완료: 총 %d 청크", company_name, total)
    return total


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_company_info(info: DartCompanyInfo) -> str:
    _cls = {"Y": "유가증권시장", "K": "코스닥", "N": "코넥스", "E": "기타"}
    lines = [
        f"[DART 기업정보] {info.corp_name}",
        f"고유번호: {info.corp_code}",
        f"종목코드: {info.stock_code}",
        f"대표이사: {info.ceo_nm}",
        f"상장구분: {_cls.get(info.corp_cls, info.corp_cls)}",
        f"사업자등록번호: {info.bizr_no}",
        f"주소: {info.adres}",
        f"홈페이지: {info.hm_url}",
        f"설립일: {info.est_dt}",
        f"결산월: {info.acc_mt}월",
    ]
    return "\n".join(line for line in lines if line.split(": ", 1)[-1])


def _fmt_financial_statements(
    stmts: list[DartFinancialItem],
    company_name: str,
    year: str,
) -> str:
    # 재무제표 종류별 그룹핑
    groups: dict[str, list[DartFinancialItem]] = {}
    for item in sorted(stmts, key=lambda x: x.ord):
        groups.setdefault(item.sj_nm, []).append(item)

    def _amount(raw: str) -> str:
        raw = raw.strip()
        if not raw or raw == "-":
            return "-"
        try:
            val = int(raw.replace(",", ""))
            if abs(val) >= 1_000_000_000_000:
                return f"{val / 1_000_000_000_000:.2f}조원"
            if abs(val) >= 100_000_000:
                return f"{val / 100_000_000:.1f}억원"
            return f"{val:,}원"
        except ValueError:
            return raw

    parts = [f"[DART 재무제표] {company_name} ({year}년 연결 기준)"]
    for sj_nm, items in groups.items():
        parts.append(f"\n■ {sj_nm}")
        for item in items[:40]:    # 계정 수 제한
            curr = _amount(item.thstrm_amount)
            prev = _amount(item.frmtrm_amount)
            parts.append(f"  {item.account_nm}: {curr}  (전기: {prev})")

    return "\n".join(parts)


def _fmt_disclosures(disclosures: list[dict], company_name: str) -> str:
    parts = [f"[DART 공시목록] {company_name} 최근 1년간 주요 공시"]
    for d in disclosures[:50]:
        parts.append(
            f"  [{d.get('rcept_dt', '')}] {d.get('report_nm', '')} "
            f"(제출인: {d.get('flr_nm', '')})"
        )
    return "\n".join(parts)
