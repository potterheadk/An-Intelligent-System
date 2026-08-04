"""Ollama model adapter.

This module provides an integration with a local Ollama server,
measuring generation latency and extracting token telemetry directly
from the Ollama API response.
"""

import time
import requests
from models.base import BaseModel, ModelResponse
from core.config import settings


class OllamaModel(BaseModel):
    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
    ):
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout

    def healthcheck(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ModelResponse:
        start_time = time.perf_counter()

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()
        data = response.json()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        content = data.get("response", "").strip()
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return ModelResponse(
            content=content,
            model_name=self.model_name,
            latency_ms=round(elapsed_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,  # Local model running on hardware = 0 marginal API cost
        )