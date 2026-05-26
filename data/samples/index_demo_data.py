"""
Index demo documents into the Hybrid RAG engine.
Run once before executing the demo or starting the Streamlit app.

    python data/samples/index_demo_data.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.retrieval import ChunkMetadata
from src.tools.hybrid_retriever import HybridRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

SAMPLES_DIR = Path(__file__).parent
DEAL_ID = "demo_acme_ai"

DOCUMENTS = [
    (
        "acme_ai_im.txt",
        ChunkMetadata(
            source_document="Acme_AI_IM_Dec2024.pdf",
            section="Information Memorandum",
            date="2024-12-01",
            deal_id=DEAL_ID,
        ),
    ),
    (
        "market_research.txt",
        ChunkMetadata(
            source_document="AI_Infrastructure_Market_Research_Q1_2025.pdf",
            section="Market Research",
            date="2025-01-15",
            deal_id=DEAL_ID,
        ),
    ),
]


def main() -> None:
    retriever = HybridRetriever.build()

    for filename, metadata in DOCUMENTS:
        path = SAMPLES_DIR / filename
        if not path.exists():
            print(f"  [SKIP] {filename} not found at {path}")
            continue
        text = path.read_text(encoding="utf-8")
        chunks = retriever.index_text(text, metadata)
        print(f"  [OK]   {filename} → {len(chunks)} chunk(s) indexed")

    print(f"\nDone. ChromaDB has {retriever._vector_store.count} total chunk(s).")
    print("You can now run:  streamlit run app/main.py")


if __name__ == "__main__":
    main()
