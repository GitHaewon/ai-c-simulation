import logging
from abc import ABC, abstractmethod

from src.models.state import ICState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Common interface for all IC agent nodes."""

    agent_id: str

    def __call__(self, state: ICState) -> dict:
        logger.info("[%s] starting", self.agent_id)
        try:
            result = self.run(state)
            logger.info("[%s] complete", self.agent_id)
            return result
        except Exception as exc:
            logger.error("[%s] failed: %s", self.agent_id, exc)
            return {"error_log": [f"{self.agent_id}: {exc}"]}

    @abstractmethod
    def run(self, state: ICState) -> dict:
        """Execute agent logic and return a partial state update dict."""
