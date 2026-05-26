import hashlib
import logging
from dataclasses import dataclass

from transformers import AutoTokenizer

from src.models.retrieval import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)

# Per CLAUDE.md §6: do not change without benchmarking retrieval quality.
DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 64


@dataclass
class ChunkerConfig:
    model_name: str
    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP


class TextChunker:
    """
    Splits raw text into token-bounded chunks with overlap.
    Uses the embedding model's own tokenizer for accurate token counts.
    """

    def __init__(self, config: ChunkerConfig) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self._chunk_size = config.chunk_size
        self._overlap = config.overlap
        logger.info(
            "TextChunker ready (model=%s, chunk=%d, overlap=%d)",
            config.model_name, config.chunk_size, config.overlap,
        )

    def chunk(self, text: str, metadata: ChunkMetadata) -> list[Chunk]:
        """Split `text` into overlapping chunks and attach `metadata` to each."""
        token_ids: list[int] = self._tokenizer.encode(text, add_special_tokens=False)
        windows = self._sliding_windows(token_ids)

        chunks: list[Chunk] = []
        for idx, window in enumerate(windows):
            chunk_text = self._tokenizer.decode(window, skip_special_tokens=True)
            chunk_meta = metadata.model_copy(update={"chunk_index": idx})
            chunk_id = self._make_id(metadata.source_document, idx)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    token_count=len(window),
                    metadata=chunk_meta,
                )
            )

        logger.debug(
            "Chunked '%s' → %d chunks", metadata.source_document, len(chunks)
        )
        return chunks

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sliding_windows(self, token_ids: list[int]) -> list[list[int]]:
        windows: list[list[int]] = []
        start = 0
        while start < len(token_ids):
            end = min(start + self._chunk_size, len(token_ids))
            windows.append(token_ids[start:end])
            if end == len(token_ids):
                break
            start += self._chunk_size - self._overlap
        return windows

    @staticmethod
    def _make_id(source: str, index: int) -> str:
        raw = f"{source}::{index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
