import logging
import re

from rank_bm25 import BM25Okapi

from src.models.retrieval import Chunk

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """
    Lower-case word tokeniser.
    Preserves numeric tokens intact — critical for financial figures and tickers
    (per CLAUDE.md §6: sparse retrieval mandatory for exact numeric/entity matching).
    """
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())


class BM25Retriever:
    """
    In-memory BM25 (Okapi) sparse retriever backed by rank-bm25.
    Must be rebuilt when the corpus changes via `index()`.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index(self, chunks: list[Chunk]) -> None:
        """Build BM25 index from the full corpus (replaces any existing index)."""
        self._chunks = list(chunks)
        tokenized = [_tokenize(c.text) for c in self._chunks]
        self._bm25 = BM25Okapi(tokenized)
        logger.info("BM25 index built — %d documents", len(self._chunks))

    def add_chunks(self, new_chunks: list[Chunk]) -> None:
        """Append chunks and rebuild the index."""
        self._chunks.extend(new_chunks)
        self.index(self._chunks)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        metadata_filter: dict | None = None,
    ) -> list[tuple[str, float]]:
        """
        Return (chunk_id, bm25_score) pairs, descending by score.
        Applies `metadata_filter` as exact-match pre-filter before scoring.
        """
        if self._bm25 is None or not self._chunks:
            logger.warning("BM25 index is empty — return no results")
            return []

        corpus = self._chunks
        if metadata_filter:
            corpus = self._apply_filter(corpus, metadata_filter)
            if not corpus:
                return []

        tokens = _tokenize(query_text)
        scores = self._bm25.get_scores(tokens)

        # Map filtered corpus indices back to original indices
        filtered_ids = {c.chunk_id for c in corpus}
        scored = [
            (chunk.chunk_id, float(scores[i]))
            for i, chunk in enumerate(self._chunks)
            if chunk.chunk_id in filtered_ids and scores[i] > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        logger.debug("BM25 query='%s' → %d results", query_text[:60], len(scored))
        return scored[:top_k]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_filter(chunks: list[Chunk], filters: dict) -> list[Chunk]:
        """Keep only chunks whose metadata satisfies all filter key=value pairs."""
        result: list[Chunk] = []
        for chunk in chunks:
            meta_dict = chunk.metadata.to_chroma_dict()
            if all(meta_dict.get(k) == v for k, v in filters.items()):
                result.append(chunk)
        return result

    def get_chunk_by_id(self, chunk_id: str) -> Chunk | None:
        for c in self._chunks:
            if c.chunk_id == chunk_id:
                return c
        return None

    @property
    def corpus_size(self) -> int:
        return len(self._chunks)
