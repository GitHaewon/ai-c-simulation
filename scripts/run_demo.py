"""
End-to-end demo runner (CLI, no Streamlit).

    python scripts/run_demo.py [--index-only]

Steps:
  1. Index demo documents into Hybrid RAG
  2. Run the full IC pipeline (agents + shock simulation + memo generation)
  3. Save outputs to data/output/
"""
import argparse
import json
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
logger = logging.getLogger("run_demo")


def index_documents() -> object:
    from src.models.retrieval import ChunkMetadata
    from src.tools.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever.build()
    samples = Path("data/samples")
    DOCS = [
        ("acme_ai_im.txt",      ChunkMetadata(source_document="Acme_AI_IM_Dec2024.pdf",         section="IM",             date="2024-12-01", deal_id="demo_acme_ai")),
        ("market_research.txt", ChunkMetadata(source_document="AI_Infra_Market_Research_2025.pdf", section="Market Research", date="2025-01-15", deal_id="demo_acme_ai")),
    ]
    for fname, meta in DOCS:
        path = samples / fname
        if path.exists():
            chunks = retriever.index_text(path.read_text(encoding="utf-8"), meta)
            logger.info("Indexed %s → %d chunks", fname, len(chunks))
        else:
            logger.warning("File not found: %s", path)
    logger.info("ChromaDB total: %d chunks", retriever._vector_store.count)
    return retriever


def run_pipeline(retriever) -> None:
    import json
    from src.core.pipeline import ICPipeline
    from src.core.llm.claude_client import ClaudeClient
    from src.models.deal import DealInput
    from src.services.memo_exporter import export_json, export_markdown, export_pptx

    # Load demo deal
    deal_path = Path("data/samples/demo_deal.json")
    deal_data = json.loads(deal_path.read_text(encoding="utf-8"))
    deal = DealInput(**deal_data)

    client = ClaudeClient()
    pipeline = ICPipeline(client, retriever)

    logger.info("=" * 60)
    logger.info("Starting IC simulation for: %s", deal.company_name)
    logger.info("=" * 60)

    result = pipeline.run(deal, progress_cb=lambda m: logger.info(m))

    # ── Print summary ──────────────────────────────────────────────────────────
    chair = result.state.get("chairman_output")
    print("\n" + "=" * 60)
    print(f"  FINAL DECISION : {chair.final_decision.value if chair else 'N/A'}")
    print(f"  VOTE TALLY     : {chair.vote_tally if chair else {}}")
    print(f"  BASE IRR       : {(result.simulation.base_case.irr or 0)*100:.1f}%")
    print(f"  BASE MOIC      : {result.simulation.base_case.moic:.2f}x")
    print("=" * 60 + "\n")

    # ── Save outputs ───────────────────────────────────────────────────────────
    out = Path("data/output")
    out.mkdir(parents=True, exist_ok=True)

    export_json(result.memo,     out / "ic_memo.json")
    export_markdown(result.memo, out / "ic_memo.md")
    export_pptx(result.memo,     out / "ic_memo.pptx")

    logger.info("Outputs saved to data/output/")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-only", action="store_true",
                        help="Only index demo documents, do not run pipeline")
    args = parser.parse_args()

    retriever = index_documents()
    if args.index_only:
        print("Indexing complete. Run without --index-only to start the pipeline.")
        return
    run_pipeline(retriever)


if __name__ == "__main__":
    main()
