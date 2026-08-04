"""Base model contract for local and remote model integrations.

This module defines the ModelResponse telemetry structure and the abstract
BaseModel interface used by model provider implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelResponse:
    content: str
    model_name: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float = 0.0


class BaseModel(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ModelResponse:
        """Generate a response from the model with telemetry metadata."""
        pass

    @abstractmethod
    def healthcheck(self) -> bool:
        """Check if the model provider endpoint is reachable and ready."""
        pass