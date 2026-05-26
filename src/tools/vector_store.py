import logging
import os
from dataclasses import dataclass, field

import chromadb
from chromadb import Collection

from src.models.retrieval import Chunk
from src.tools.embedder import Embedder

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIR = "./data/chroma"
DEFAULT_COLLECTION = "ic_simulation"


@dataclass
class VectorStoreConfig:
    persist_dir: str = field(
        default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", DEFAULT_PERSIST_DIR)
    )
    collection_name: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_COLLECTION)
    )


class VectorStore:
    """
    ChromaDB-backed dense retriever.
    Embeddings are pre-computed externally (via Embedder) and passed in.
    """

    def __init__(self, embedder: Embedder, config: VectorStoreConfig | None = None) -> None:
        cfg = config or VectorStoreConfig()
        self._embedder = embedder
        self._client = chromadb.PersistentClient(path=cfg.persist_dir)
        self._collection: Collection = self._client.get_or_create_collection(
            name=cfg.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready (collection='%s', docs=%d)",
            cfg.collection_name, self._collection.count(),
        )

    # ── Indexing ──────────────────────────────────────────────────────────────

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        texts = [c.text for c in chunks]
        embeddings = self._embedder.encode(texts).tolist()
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[c.metadata.to_chroma_dict() for c in chunks],
        )
        logger.info("Indexed %d chunks into ChromaDB", len(chunks))

    def delete_by_deal(self, deal_id: str) -> None:
        """Remove all chunks belonging to a specific deal."""
        self._collection.delete(where={"deal_id": {"$eq": deal_id}})
        logger.info("Deleted chunks for deal_id='%s'", deal_id)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        metadata_filter: dict | None = None,
    ) -> list[tuple[str, float]]:
        """
        Return (chunk_id, cosine_similarity_score) pairs, descending by score.
        `metadata_filter` follows ChromaDB `where` syntax.
        """
        query_embedding = self._embedder.encode_one(query_text).tolist()
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, max(self._collection.count(), 1)),
            "include": ["distances"],
        }
        if metadata_filter:
            kwargs["where"] = metadata_filter

        results = self._collection.query(**kwargs)
        ids: list[str] = results["ids"][0]
        # ChromaDB returns L2 or cosine distance; convert to similarity
        distances: list[float] = results["distances"][0]
        scores = [1.0 - d for d in distances]  # cosine distance → similarity

        logger.debug(
            "VectorStore query='%s' → %d results", query_text[:60], len(ids)
        )
        return list(zip(ids, scores))

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """Fetch full Chunk objects for a list of ids."""
        from src.models.retrieval import ChunkMetadata

        if not chunk_ids:
            return []
        result = self._collection.get(ids=chunk_ids, include=["documents", "metadatas"])
        chunks: list[Chunk] = []
        for cid, doc, meta in zip(result["ids"], result["documents"], result["metadatas"]):
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    text=doc,
                    token_count=0,  # not stored; set during indexing
                    metadata=ChunkMetadata.from_chroma_dict(meta),
                )
            )
        return chunks

    @property
    def count(self) -> int:
        return self._collection.count()
