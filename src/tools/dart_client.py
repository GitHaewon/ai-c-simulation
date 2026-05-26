"""
DART(전자공시시스템) API 클라이언트.
https://opendart.fss.or.kr — 금융감독원 전자공시 Open API

DART_API_KEY 환경변수 필요 (https://opendart.fss.or.kr/intro/main.do).
API 키 없으면 is_available=False — 빈 결과 반환 (graceful degradation).
"""
import io
import logging
import os
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://opendart.fss.or.kr/api"
_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)

# ── 주요 한국 대기업 corp_code 사전 ────────────────────────────────────────────
# DART 고유번호: https://opendart.fss.or.kr 에서 확인
_KNOWN_CORPS: dict[str, str] = {
    "삼성전자":         "00126380",
    "samsung electronics": "00126380",
    "samsung":         "00126380",
    "sk하이닉스":       "00164779",
    "sk hynix":        "00164779",
    "네이버":           "00266961",
    "naver":            "00266961",
    "카카오":           "00918444",
    "kakao":            "00918444",
    "lg전자":           "00401731",
    "lg electronics":  "00401731",
    "현대자동차":       "00164742",
    "hyundai motor":   "00164742",
    "포스코":           "00049530",
    "posco holdings":  "00049530",
    "posco":            "00049530",
    "셀트리온":         "00519870",
    "celltrion":        "00519870",
    "기아":             "00164807",
    "kia":              "00164807",
    "삼성바이오로직스":  "00877059",
    "sk텔레콤":         "00178872",
    "skt":              "00178872",
    "kt":               "00781234",
    "하이브":           "00993448",
    "hybe":             "00993448",
    "크래프톤":         "01089509",
    "krafton":          "01089509",
    "카카오뱅크":       "01180584",
    "kakaobank":        "01180584",
    "두산에너빌리티":   "00064760",
    "한화":             "00100534",
    "롯데케미칼":       "00100534",
    "lg화학":           "00109532",
    "현대모비스":       "00164788",
}

# 사업보고서 코드
_REPRT_ANNUAL = "11011"
_REPRT_HALF   = "11012"
_REPRT_Q1     = "11013"
_REPRT_Q3     = "11014"


@dataclass
class DartCompanyInfo:
    corp_code: str
    corp_name: str
    stock_code: str = ""
    ceo_nm: str = ""
    corp_cls: str = ""   # Y=유가증권, K=코스닥, N=코넥스, E=기타
    bizr_no: str = ""
    adres: str = ""
    hm_url: str = ""
    est_dt: str = ""
    acc_mt: str = ""     # 결산월


@dataclass
class DartFinancialItem:
    account_nm: str          # 계정명
    sj_nm: str               # 재무제표명
    thstrm_amount: str = ""  # 당기금액
    frmtrm_amount: str = ""  # 전기금액
    bfefrmtrm_amount: str = ""  # 전전기금액
    ord: str = ""            # 계정과목 정렬순서


class DartClient:
    """
    금융감독원 전자공시(DART) Open API 클라이언트.

    환경변수 DART_API_KEY 설정 필요.
    미설정 시 is_available=False — 모든 메서드가 빈 결과 반환.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("DART_API_KEY", "")
        self._corp_cache: dict[str, str] = {}   # company_name → corp_code
        self._corp_list_loaded: bool = False

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    # ── 기업 고유번호 조회 ─────────────────────────────────────────────────────

    def resolve_corp_code(self, company_name: str) -> str | None:
        """
        회사명 → DART corp_code 변환.
        1순위: 캐시
        2순위: 하드코딩된 주요 기업 사전
        3순위: DART 전체 기업 목록 ZIP 다운로드 후 검색 (API 키 필요)
        """
        if company_name in self._corp_cache:
            return self._corp_cache[company_name]

        # 주요 기업 사전 (대소문자 무시, 부분 매칭)
        key = company_name.strip().lower()
        for name, code in _KNOWN_CORPS.items():
            if name == key or name in key or key in name:
                logger.info("DART corp_code (사전): '%s' → %s", company_name, code)
                self._corp_cache[company_name] = code
                return code

        if not self.is_available:
            logger.warning(
                "DART_API_KEY 미설정 — '%s' corp_code 조회 불가 (docs/KNOWN_ISSUES.md 참조)",
                company_name,
            )
            return None

        # DART 전체 기업 목록 ZIP 다운로드 (캐싱)
        if not self._corp_list_loaded:
            self._load_corp_list()

        if company_name in self._corp_cache:
            return self._corp_cache[company_name]

        logger.warning("DART corp_code 없음: '%s'", company_name)
        return None

    def _load_corp_list(self) -> None:
        """DART 전체 기업 고유번호 목록 ZIP 다운로드 후 캐싱."""
        try:
            logger.info("DART 전체 기업 목록 다운로드 중 …")
            resp = httpx.get(
                f"{_BASE}/corpCode.xml",
                params={"crtfc_key": self._api_key},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                with zf.open("CORPCODE.xml") as xml_file:
                    tree = ET.parse(xml_file)

            for item in tree.getroot().findall("list"):
                name = (item.findtext("corp_name") or "").strip()
                code = (item.findtext("corp_code") or "").strip()
                if name and code:
                    self._corp_cache[name] = code
                    self._corp_cache[name.lower()] = code

            self._corp_list_loaded = True
            logger.info("DART 기업 목록 로드 완료: %d 기업", len(self._corp_cache))
        except Exception as exc:
            logger.error("DART corpCode.xml 로드 실패: %s", exc)

    # ── 기업 기본 정보 ─────────────────────────────────────────────────────────

    def get_company_info(self, corp_code: str) -> DartCompanyInfo | None:
        if not self.is_available:
            return None
        try:
            resp = httpx.get(
                f"{_BASE}/company.json",
                params={"corp_code": corp_code, "crtfc_key": self._api_key},
                timeout=_TIMEOUT,
            )
            data = resp.json()
            if data.get("status") == "000":
                return DartCompanyInfo(
                    corp_code=corp_code,
                    corp_name=data.get("corp_name", ""),
                    stock_code=data.get("stock_code", ""),
                    ceo_nm=data.get("ceo_nm", ""),
                    corp_cls=data.get("corp_cls", ""),
                    bizr_no=data.get("bizr_no", ""),
                    adres=data.get("adres", ""),
                    hm_url=data.get("hm_url", ""),
                    est_dt=data.get("est_dt", ""),
                    acc_mt=data.get("acc_mt", ""),
                )
            logger.warning(
                "DART company.json 오류: status=%s message=%s",
                data.get("status"), data.get("message"),
            )
        except Exception as exc:
            logger.error("DART company.json 실패 (corp=%s): %s", corp_code, exc)
        return None

    # ── 재무제표 ───────────────────────────────────────────────────────────────

    def get_financial_statements(
        self,
        corp_code: str,
        year: str,
        reprt_code: str = _REPRT_ANNUAL,
        fs_div: str = "CFS",          # CFS=연결재무제표, OFS=별도재무제표
    ) -> list[DartFinancialItem]:
        """
        DART fnlttSinglAcntAll 엔드포인트 — 전체 재무제표 항목 조회.

        reprt_code:
            11011 = 사업보고서 (12월 결산)
            11012 = 반기보고서
            11013 = 1분기보고서
            11014 = 3분기보고서
        """
        if not self.is_available:
            return []
        try:
            resp = httpx.get(
                f"{_BASE}/fnlttSinglAcntAll.json",
                params={
                    "corp_code":  corp_code,
                    "bsns_year":  year,
                    "reprt_code": reprt_code,
                    "fs_div":     fs_div,
                    "crtfc_key":  self._api_key,
                },
                timeout=_TIMEOUT,
            )
            data = resp.json()
            if data.get("status") == "000":
                items = [
                    DartFinancialItem(
                        account_nm=r.get("account_nm", ""),
                        sj_nm=r.get("sj_nm", ""),
                        thstrm_amount=r.get("thstrm_amount", ""),
                        frmtrm_amount=r.get("frmtrm_amount", ""),
                        bfefrmtrm_amount=r.get("bfefrmtrm_amount", ""),
                        ord=r.get("ord", ""),
                    )
                    for r in data.get("list", [])
                ]
                logger.info(
                    "DART 재무제표 조회 성공: corp=%s year=%s → %d 항목",
                    corp_code, year, len(items),
                )
                return items
            logger.warning(
                "DART fnlttSinglAcntAll 오류: status=%s message=%s (corp=%s year=%s)",
                data.get("status"), data.get("message"), corp_code, year,
            )
        except Exception as exc:
            logger.error("DART 재무제표 실패 (corp=%s year=%s): %s", corp_code, year, exc)
        return []

    # ── 공시 목록 ──────────────────────────────────────────────────────────────

    def get_disclosure_list(
        self,
        corp_code: str,
        start_date: str,    # YYYYMMDD
        end_date: str,      # YYYYMMDD
        report_type: str = "A",  # A=사업보고서, B=주요사항보고서, C=발행공시, D=지분공시
    ) -> list[dict]:
        if not self.is_available:
            return []
        try:
            resp = httpx.get(
                f"{_BASE}/list.json",
                params={
                    "corp_code":  corp_code,
                    "bgn_de":     start_date,
                    "end_de":     end_date,
                    "pblntf_ty":  report_type,
                    "crtfc_key":  self._api_key,
                },
                timeout=_TIMEOUT,
            )
            data = resp.json()
            if data.get("status") == "000":
                return data.get("list", [])
            logger.warning(
                "DART list.json 오류: status=%s (corp=%s)", data.get("status"), corp_code,
            )
        except Exception as exc:
            logger.error("DART 공시목록 실패 (corp=%s): %s", corp_code, exc)
        return []
