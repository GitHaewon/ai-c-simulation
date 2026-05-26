"""
Smoke-test for the Hybrid RAG engine.

Run from project root:
    python scripts/test_rag.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.retrieval import ChunkMetadata
from src.tools.hybrid_retriever import HybridRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Sample documents ──────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    (
        """
        Acme AI achieved revenue of $12M in FY2024, up 180% year-over-year.
        Gross margin improved to 72%. The company operates in the AI infrastructure
        sector and competes directly with Nvidia, AMD, and several startups.
        Monthly burn rate is $800K with 18 months of runway.
        """,
        ChunkMetadata(
            source_document="Acme_AI_IM.pdf",
            section="Financial Summary",
            page=4,
            date="2024-12-01",
            deal_id="deal_001",
        ),
    ),
    (
        """
        Key risks include: (1) heavy customer concentration — top 3 customers
        represent 61% of ARR; (2) regulatory uncertainty around AI Act in the EU;
        (3) key-person dependency on the founding CTO.
        Exit comparable transactions in the sector show a median EV/Revenue of 8x.
        """,
        ChunkMetadata(
            source_document="Acme_AI_IM.pdf",
            section="Risk Factors",
            page=9,
            date="2024-12-01",
            deal_id="deal_001",
        ),
    ),
    (
        """
        Global AI infrastructure market is projected to reach $250B by 2028,
        growing at a CAGR of 38%. Hyperscaler capex on AI accelerators increased
        240% in 2024. Interest rate environment: Fed Funds Rate at 4.5% as of Q1 2025.
        """,
        ChunkMetadata(
            source_document="Market_Research_2025.pdf",
            section="Market Sizing",
            page=2,
            date="2025-01-15",
            deal_id="deal_001",
        ),
    ),
]


def test_index_and_retrieve() -> None:
    retriever = HybridRetriever.build()

    print("\n── Indexing documents …")
    for text, metadata in SAMPLE_DOCS:
        chunks = retriever.index_text(text.strip(), metadata)
        print(f"  {metadata.source_document} §{metadata.section} → {len(chunks)} chunk(s)")

    print("\n── Test 1: financial query")
    result = retriever.retrieve("What is the revenue and gross margin?", top_k=3)
    _print_result(result)
    assert result.total_retrieved > 0, "Must return at least one chunk"

    print("\n── Test 2: risk query")
    result = retriever.retrieve("customer concentration and regulatory risk", top_k=3)
    _print_result(result)

    print("\n── Test 3: metadata filter (deal_id)")
    result = retriever.retrieve(
        "interest rate macro environment",
        top_k=5,
        metadata_filter={"deal_id": "deal_001"},
    )
    _print_result(result)
    assert all(r.chunk.metadata.deal_id == "deal_001" for r in result.chunks)

    print("\n── Test 4: citation formatting")
    context = HybridRetriever.format_context_with_citations(result)
    print(context[:400], "…")

    print("\ntest_index_and_retrieve PASSED")


def _print_result(result) -> None:  # type: ignore[no-untyped-def]
    print(f"  Query   : {result.query}")
    print(f"  Results : {result.total_retrieved}")
    for r in result.chunks:
        print(
            f"    [{r.chunk.chunk_id[:8]}] score={r.score:.4f} "
            f"d_rank={r.dense_rank} s_rank={r.sparse_rank} "
            f"| {r.chunk.metadata.source_document} §{r.chunk.metadata.section}"
        )


if __name__ == "__main__":
    test_index_and_retrieve()
