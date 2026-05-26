from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    source_document: str
    section: str = ""
    page: int = 0
    date: str = ""
    deal_id: str = ""
    chunk_index: int = 0
    company_name: str = ""  # entity match filter — always set when indexing real data

    def to_chroma_dict(self) -> dict:
        """ChromaDB only accepts flat str/int/float/bool metadata values."""
        return {
            "source_document": self.source_document,
            "section": self.section,
            "page": self.page,
            "date": self.date,
            "deal_id": self.deal_id,
            "chunk_index": self.chunk_index,
            "company_name": self.company_name,
        }

    @classmethod
    def from_chroma_dict(cls, d: dict) -> "ChunkMetadata":
        known = {f for f in cls.model_fields}
        return cls(**{k: v for k, v in d.items() if k in known})


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
