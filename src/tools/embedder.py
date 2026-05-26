import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class Embedder:
    """
    Wraps SentenceTransformer for batch text encoding.
    All agents share one instance to avoid reloading the model.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        logger.info("Embedding model ready")

    @property
    def model_name(self) -> str:
        return self._model_name

    def encode(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        """Return L2-normalised embeddings, shape (n, dim)."""
        embeddings: np.ndarray = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return embeddings

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    @property
    def embedding_dim(self) -> int:
        return self._model.get_sentence_embedding_dimension()
