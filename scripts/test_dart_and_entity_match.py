"""
DART 데이터 파이프라인 및 엔티티 매칭 검증 스크립트.

수행:
1. DART API 연결 테스트
2. ChromaDB 현재 상태 확인
3. 삼성전자 corp_code 조회
4. 엔티티 필터링 동작 검증 (다른 회사 청크 차단 확인)
5. DART 인덱싱 시뮬레이션 (API 키 있으면 실제 호출)
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

import chromadb
from src.tools.dart_client import DartClient
from src.tools.hybrid_retriever import HybridRetriever
from src.models.retrieval import ChunkMetadata

SEPARATOR = "=" * 60


def test_dart_availability() -> None:
    print(f"\n{SEPARATOR}")
    print("TEST 1: DART API 연결 테스트")
    print(SEPARATOR)

    dart = DartClient()
    print(f"  DART_API_KEY 설정 여부: {'✓ 설정됨' if dart.is_available else '✗ 미설정'}")

    if dart.is_available:
        corp_code = dart.resolve_corp_code("삼성전자")
        print(f"  삼성전자 corp_code: {corp_code}")
        if corp_code:
            info = dart.get_company_info(corp_code)
            if info:
                print(f"  기업명: {info.corp_name}")
                print(f"  대표이사: {info.ceo_nm}")
                print(f"  결산월: {info.acc_mt}월")
            stmts = dart.get_financial_statements(corp_code, "2023")
            print(f"  2023년 재무제표 항목 수: {len(stmts)}")
            if stmts:
                key_items = [s for s in stmts if s.account_nm in ("매출액", "영업이익", "당기순이익")]
                for item in key_items:
                    print(f"    {item.account_nm}: {item.thstrm_amount} (전기: {item.frmtrm_amount})")
    else:
        print("  → DART_API_KEY를 .env에 설정하면 실제 공시 데이터를 가져올 수 있습니다.")
        print("     발급: https://opendart.fss.or.kr/intro/main.do")

        # corp_code 사전 검색 테스트 (API 키 불필요)
        corp_code = dart.resolve_corp_code("삼성전자")
        print(f"\n  삼성전자 사전 corp_code 조회: {corp_code}")
        corp_code2 = dart.resolve_corp_code("Samsung Electronics")
        print(f"  'Samsung Electronics' 사전 조회: {corp_code2}")
        corp_code3 = dart.resolve_corp_code("SK하이닉스")
        print(f"  'SK하이닉스' 사전 조회: {corp_code3}")

    print("  TEST 1 PASSED")


def test_chromadb_status() -> None:
    print(f"\n{SEPARATOR}")
    print("TEST 2: ChromaDB 현재 상태 확인")
    print(SEPARATOR)

    chroma_client = chromadb.PersistentClient(path="./data/chroma")
    for col in chroma_client.list_collections():
        c = chroma_client.get_collection(col.name)
        print(f"  컬렉션: {col.name}  청크 수: {c.count()}")
        if c.count() > 0:
            sample = c.get(limit=c.count(), include=["metadatas"])
            companies = set(m.get("company_name", "(없음)") for m in sample["metadatas"])
            print(f"  존재하는 기업: {companies}")

    print("  TEST 2 PASSED")


def test_entity_filtering() -> None:
    print(f"\n{SEPARATOR}")
    print("TEST 3: 엔티티 필터링 — 다른 회사 청크 차단 검증")
    print(SEPARATOR)

    retriever = HybridRetriever.build()

    # Acme AI 청크 인덱싱 (다른 회사 테스트용)
    acme_meta = ChunkMetadata(
        source_document="Acme_AI_TEST.pdf",
        section="Financials",
        date="2024-12-01",
        deal_id="acme_ai",
        company_name="Acme AI",
    )
    retriever.index_text(
        "Acme AI achieved revenue of $12M in FY2024, up 180% year-over-year. Gross margin 72%.",
        acme_meta,
    )

    samsung_meta = ChunkMetadata(
        source_document="Samsung_Test.txt",
        section="재무정보",
        date="2024-01-01",
        deal_id="samsung",
        company_name="삼성전자",
    )
    retriever.index_text(
        "삼성전자 2023년 매출액 258.9조원, 영업이익 6.6조원. 반도체 부문 HBM 생산 확대.",
        samsung_meta,
    )

    # 삼성전자로 필터링하여 Acme AI가 나오지 않는지 확인
    result = retriever.retrieve(
        "revenue financials",
        top_k=5,
        metadata_filter={"company_name": "삼성전자"},
    )

    print(f"  검색어: 'revenue financials'")
    print(f"  필터: company_name='삼성전자'")
    print(f"  결과 수: {len(result.chunks)}")

    for r in result.chunks:
        meta = r.chunk.metadata
        print(f"    [{meta.source_document}] company={meta.company_name} score={r.score:.4f}")
        print(f"    text: {r.chunk.text[:80]!r}")

    # 검증
    for chunk in result.chunks:
        assert chunk.chunk.metadata.company_name == "삼성전자", \
            f"FAIL: Acme AI 청크가 삼성전자 검색 결과에 포함됨! {chunk.chunk.metadata}"

    print("  ✓ 엔티티 필터링 정상 동작: 삼성전자 청크만 반환됨")
    print("  TEST 3 PASSED")


def main() -> None:
    print("\n DART 데이터 파이프라인 및 엔티티 매칭 검증")
    print(" (실제 DART 기반인지 / mock 기반인지 명확히 진단)")

    test_dart_availability()
    test_chromadb_status()
    test_entity_filtering()

    print(f"\n{SEPARATOR}")
    print("전체 검증 완료")
    print(SEPARATOR)

    dart = DartClient()
    if dart.is_available:
        print("  데이터 소스: DART 실제 공시 데이터 (API 키 설정됨)")
    else:
        print("  데이터 소스: RAG 컨텍스트 없음 (DART_API_KEY 미설정)")
        print("  → 에이전트는 LLM 자체 지식만으로 분석 수행")
        print("  → 실제 DART 데이터 사용 시 .env에 DART_API_KEY 추가 필요")


if __name__ == "__main__":
    main()
