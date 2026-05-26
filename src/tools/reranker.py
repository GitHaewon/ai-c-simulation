import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Standard RRF constant — lower k rewards high-rank results more strongly.
RRF_K = 60


@dataclass
class RankedResult:
    chunk_id: str
    rrf_score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None


def reciprocal_rank_fusion(
    dense_results: list[tuple[str, float]],
    sparse_results: list[tuple[str, float]],
    top_k: int = 5,
    k: int = RRF_K,
) -> list[RankedResult]:
    """
    Combine dense and sparse result lists using Reciprocal Rank Fusion.

    RRF score = Σ  1 / (k + rank_i)
    Ranks are 1-based; a chunk missing from one list is simply not scored
    for that retriever.

    Parameters
    ----------
    dense_results:  [(chunk_id, similarity_score), ...]  descending
    sparse_results: [(chunk_id, bm25_score), ...]        descending
    top_k:          number of results to return
    k:              RRF smoothing constant (default 60)
    """
    rrf_scores: dict[str, float] = {}
    dense_ranks: dict[str, int] = {}
    sparse_ranks: dict[str, int] = {}

    for rank, (chunk_id, _) in enumerate(dense_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        dense_ranks[chunk_id] = rank

    for rank, (chunk_id, _) in enumerate(sparse_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        sparse_ranks[chunk_id] = rank

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = [
        RankedResult(
            chunk_id=cid,
            rrf_score=round(score, 6),
            dense_rank=dense_ranks.get(cid),
            sparse_rank=sparse_ranks.get(cid),
        )
        for cid, score in ranked[:top_k]
    ]

    logger.debug(
        "RRF fusion: dense=%d + sparse=%d → top-%d (unique=%d)",
        len(dense_results), len(sparse_results), top_k, len(rrf_scores),
    )
    return results
