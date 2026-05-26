from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    source_document: str
    section: str = ""
    page: int = 0
    date: str = ""
    deal_id: str = ""
    chunk_index: int = 0

    def to_chroma_dict(self) -> dict:
        """ChromaDB only accepts flat str/int/float/bool metadata values."""
        return {
            "source_document": self.source_document,
            "section": self.section,
            "page": self.page,
            "date": self.date,
            "deal_id": self.deal_id,
            "chunk_index": self.chunk_index,
        }

    @classmethod
    def from_chroma_dict(cls, d: dict) -> "ChunkMetadata":
        return cls(**d)


class Chunk(BaseModel):
    chunk_id: str
    text: str
    token_count: int
    metadata: ChunkMetadata


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float = Field(ge=0.0, description="RRF score after reranking")
    dense_rank: int | None = None
    sparse_rank: int | None = None


class RetrievalResult(BaseModel):
    query: str
    chunks: list[RetrievedChunk]
    total_retrieved: int
    metadata_filter: dict = Field(default_factory=dict)
