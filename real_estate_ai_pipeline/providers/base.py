"""Base class for AI model providers.

Defines a unified interface that allows switching between
different model backends (Kilo Code API, local Qwen, etc.)
by changing only the provider configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the provider. Returns True if ready."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model backend is reachable."""
        raise NotImplementedError

    @abstractmethod
    def classify(self, text: str) -> Dict[str, Any]:
        """Classify a Facebook post into a listing category.

        Returns a dict with keys:
            - category: one of the six listing types
            - confidence: float between 0 and 1
            - reasoning: short explanation
        """
        raise NotImplementedError

    @abstractmethod
    def extract(self, text: str, category: str) -> Dict[str, Any]:
        """Extract structured listing fields from post text.

        Returns a dict matching the listing schema fields.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        raise NotImplementedError
