import logging
from abc import ABC, abstractmethod

from openai import APIError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, Field

from app.services.exceptions import LlmProviderException, LlmRateLimitException

logger = logging.getLogger(__name__)


class LlmResponse(BaseModel):
    content: str = Field(..., min_length=1)
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    model: str = Field(..., min_length=1)


class BaseLlmProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
    ) -> LlmResponse:
        pass


class OpenAiLlmProvider(BaseLlmProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        if not model:
            raise ValueError("model is required")

        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
    ) -> LlmResponse:
        if not system_prompt:
            raise ValueError("system_prompt is required")
        if not user_prompt:
            raise ValueError("user_prompt is required")

        input_messages = [
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict = {
            "model": self.model,
            "input": input_messages,
        }

        reasoning_effort = self._temperature_to_effort(self.temperature)
        kwargs["reasoning"] = {"effort": reasoning_effort}

        if response_format and response_format.get("type") == "json_object":
            kwargs["text"] = {"format": {"type": "json_object"}}

        try:
            response = await self.client.responses.create(**kwargs)
        except RateLimitError as e:
            logger.error("LLM rate limit hit: %s", str(e))
            raise LlmRateLimitException(f"LLM rate limit exceeded: {str(e)}") from e
        except APIError as e:
            logger.error("LLM API error: %s", str(e))
            raise LlmProviderException(f"LLM API call failed: {str(e)}") from e

        content = response.output_text or ""

        usage = response.usage
        prompt_tokens = usage.input_tokens if usage else 0
        completion_tokens = usage.output_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        return LlmResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=response.model,
        )

    def _temperature_to_effort(self, temperature: float) -> str:
        if temperature <= 0.2:
            return "low"
        if temperature <= 0.5:
            return "medium"
        return "high"
