import logging

from src.models.retrieval import Chunk, ChunkMetadata, RetrievalResult, RetrievedChunk
from src.tools.bm25_retriever import BM25Retriever
from src.tools.chunker import ChunkerConfig, TextChunker
from src.tools.embedder import DEFAULT_EMBEDDING_MODEL, Embedder
from src.tools.reranker import reciprocal_rank_fusion
from src.tools.vector_store import VectorStore, VectorStoreConfig

logger = logging.getLogger(__name__)

# Per CLAUDE.md §6: default top-K after reranking.
DEFAULT_TOP_K = 5

# Retrieval pool fed into RRF before trimming to top-K.
_CANDIDATE_POOL = 20


class HybridRetriever:
    """
    Public interface for the RAG pipeline.

    Usage
    -----
    retriever = HybridRetriever.build()
    retriever.index_text("raw document text", ChunkMetadata(...))
    results = retriever.retrieve("what is the revenue growth?", top_k=5)
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        bm25: BM25Retriever,
        chunker: TextChunker,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._bm25 = bm25
        self._chunker = chunker
        logger.info("HybridRetriever initialised")

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def build(
        cls,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        vector_store_config: VectorStoreConfig | None = None,
    ) -> "HybridRetriever":
        """Convenience factory — creates and wires all components."""
        embedder = Embedder(model_name=embedding_model)
        vector_store = VectorStore(embedder=embedder, config=vector_store_config)
        bm25 = BM25Retriever()
        chunker = TextChunker(
            ChunkerConfig(model_name=embedding_model)
        )
        return cls(embedder, vector_store, bm25, chunker)

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_text(self, text: str, metadata: ChunkMetadata) -> list[Chunk]:
        """Chunk raw text and index into both dense and sparse stores."""
        chunks = self._chunker.chunk(text, metadata)
        self._vector_store.add_chunks(chunks)
        self._bm25.add_chunks(chunks)
        logger.info(
            "Indexed '%s' → %d chunks (dense=%d, sparse=%d)",
            metadata.source_document, len(chunks),
            self._vector_store.count, self._bm25.corpus_size,
        )
        return chunks

    def index_chunks(self, chunks: list[Chunk]) -> None:
        """Index pre-built Chunk objects directly."""
        self._vector_store.add_chunks(chunks)
        self._bm25.add_chunks(chunks)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        metadata_filter: dict | None = None,
    ) -> RetrievalResult:
        """
        Hybrid retrieval: dense + sparse → RRF → top-K RetrievedChunks.

        Per CLAUDE.md §6: all calls are logged with query, chunk IDs, and scores.
        """
        dense_results = self._vector_store.query(
            query, top_k=_CANDIDATE_POOL, metadata_filter=metadata_filter
        )
        sparse_results = self._bm25.query(
            query, top_k=_CANDIDATE_POOL, metadata_filter=metadata_filter
        )

        fused = reciprocal_rank_fusion(dense_results, sparse_results, top_k=top_k)

        # Resolve chunk objects from vector store (source of truth for full text).
        chunk_ids = [r.chunk_id for r in fused]
        chunk_map: dict[str, Chunk] = {
            c.chunk_id: c
            for c in self._vector_store.get_chunks_by_ids(chunk_ids)
        }

        retrieved: list[RetrievedChunk] = []
        for ranked in fused:
            chunk = chunk_map.get(ranked.chunk_id)
            if chunk is None:
                # Fall back to BM25 in-memory store if not in ChromaDB
                chunk = self._bm25.get_chunk_by_id(ranked.chunk_id)
            if chunk is None:
                logger.warning("chunk_id '%s' not found — skipping", ranked.chunk_id)
                continue
            retrieved.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=ranked.rrf_score,
                    dense_rank=ranked.dense_rank,
                    sparse_rank=ranked.sparse_rank,
                )
            )

        result = RetrievalResult(
            query=query,
            chunks=retrieved,
            total_retrieved=len(retrieved),
            metadata_filter=metadata_filter or {},
        )

        # Per CLAUDE.md §6: log query, retrieved chunk IDs, and scores.
        logger.info(
            "retrieve | query='%s' | filter=%s | results=%d | ids=%s | scores=%s",
            query[:80],
            metadata_filter,
            len(retrieved),
            [r.chunk.chunk_id for r in retrieved],
            [round(r.score, 4) for r in retrieved],
        )
        return result

    # ── Citation helper ───────────────────────────────────────────────────────

    @staticmethod
    def format_context_with_citations(result: RetrievalResult) -> str:
        """
        Format retrieved chunks into a prompt-ready string with inline citations.
        Agents inject this under the '## Retrieved Context' header per CLAUDE.md §7.
        """
        sections: list[str] = []
        for i, r in enumerate(result.chunks, start=1):
            meta = r.chunk.metadata
            citation = (
                f"[{i}] {meta.source_document}"
                + (f", §{meta.section}" if meta.section else "")
                + (f", p.{meta.page}" if meta.page else "")
                + (f" ({meta.date})" if meta.date else "")
            )
            sections.append(f"{citation}\n{r.chunk.text}")
        return "\n\n---\n\n".join(sections)
