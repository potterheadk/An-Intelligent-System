"""Gemini model adapter.

This module provides a Gemini integration using the Gemini REST API or
OpenAI-compatible endpoints, with full support for system prompts, latency
tracking, and token usage telemetry.
"""

import time
import requests
from models.base import BaseModel, ModelResponse
from core.config import settings


class GeminiModel(BaseModel):
    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 120,
    ):
        self.model_name = model_name or settings.GEMINI_MODEL
        self.base_url = (base_url or settings.GEMINI_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["x-goog-api-key"] = self.api_key
        return headers

    def _is_openai_compatible(self) -> bool:
        return "/openai" in self.base_url

    def healthcheck(self) -> bool:
        if not self.api_key:
            return False

        try:
            if self._is_openai_compatible():
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                    timeout=10,
                )
            else:
                response = requests.get(
                    f"{self.base_url}/models/{self.model_name}",
                    headers=self._headers(),
                    timeout=10,
                )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Standard rate estimate for Flash class models ($0.075 / 1M input, $0.30 / 1M output)
        input_cost = (input_tokens / 1_000_000.0) * 0.075
        output_cost = (output_tokens / 1_000_000.0) * 0.30
        return round(input_cost + output_cost, 6)

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ModelResponse:
        if not self.api_key:
            raise RuntimeError("Gemini API key is not configured.")

        start_time = time.perf_counter()

        if self._is_openai_compatible():
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.0,
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            content = ""
            if isinstance(data, dict) and "choices" in data and data["choices"]:
                first_choice = data["choices"][0]
                if "message" in first_choice and isinstance(first_choice["message"], dict):
                    content = str(first_choice["message"].get("content", "")).strip()
                elif "text" in first_choice:
                    content = str(first_choice.get("text", "")).strip()

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            return ModelResponse(
                content=content,
                model_name=self.model_name,
                latency_ms=round(elapsed_ms, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=self._estimate_cost(input_tokens, output_tokens),
            )

        # Standard Gemini REST API Path
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        response = requests.post(
            f"{self.base_url}/models/{self.model_name}:generateContent",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

        response.raise_for_status()
        data = response.json()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        content = ""
        if isinstance(data, dict):
            if "candidates" in data and data["candidates"]:
                first_cand = data["candidates"][0]
                if "content" in first_cand and "parts" in first_cand["content"]:
                    content = "".join(
                        part.get("text", "") for part in first_cand["content"]["parts"]
                    ).strip()

        usage_meta = data.get("usageMetadata", {})
        input_tokens = usage_meta.get("promptTokenCount", 0)
        output_tokens = usage_meta.get("candidatesTokenCount", 0)

        return ModelResponse(
            content=content,
            model_name=self.model_name,
            latency_ms=round(elapsed_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._estimate_cost(input_tokens, output_tokens),
        )