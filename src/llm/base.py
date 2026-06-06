"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod
from typing import List

from models.quintuple import Quintuple


class BaseLLM(ABC):
    """LLM interface abstraction. All providers implement this."""

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str) -> str:
        """Send a prompt and return the raw text response."""
        ...

    @abstractmethod
    def extract_quintuples(
        self, text: str, syntactic_hints: dict = None
    ) -> List[Quintuple]:
        """Extract quintuples from text with optional syntactic hints."""
        ...
