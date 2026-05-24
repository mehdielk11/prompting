"""Hugging Face client — isolated wrapper around huggingface_hub."""

from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

_HF_TOKEN: str = os.getenv("HF_API_TOKEN", "")
_MODEL_GENERATE: str = os.getenv(
    "HF_MODEL_GENERATE",
    "Qwen/Qwen2.5-7B-Instruct",  # Free on HF Serverless Inference API
)

_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds


class HFClientError(Exception):
    """Raised when the Hugging Face API returns an unrecoverable error."""


class HFClient:
    """Thin wrapper around InferenceClient with retry logic.

    Uses the chat_completion API (compatible with huggingface-hub >= 0.24).
    All methods raise HFClientError on failure after exhausting retries.
    """

    def __init__(self) -> None:
        if not _HF_TOKEN:
            raise HFClientError("HF_API_TOKEN is not set. Add it to your .env file.")
        self._client = InferenceClient(model=_MODEL_GENERATE, token=_HF_TOKEN)

    # ------------------------------------------------------------------
    # Text generation via chat_completion
    # ------------------------------------------------------------------

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using the chat completion API.

        Args:
            system_prompt: Role / context instructions for the model.
            user_prompt: The actual user request.
            max_new_tokens: Maximum tokens to generate.
            temperature: Sampling temperature (0 = deterministic).

        Returns:
            Generated text string.

        Raises:
            HFClientError: If all retries are exhausted.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        def _call():
            response = self._client.chat_completion(
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=max(temperature, 0.01),  # some models reject 0.0
            )
            return response.choices[0].message.content

        return self._call_with_retry(_call)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(self, fn, *args, **kwargs) -> Any:
        """Call *fn* with retries on transient errors.

        Args:
            fn: Callable to invoke.
            *args: Positional arguments forwarded to fn.
            **kwargs: Keyword arguments forwarded to fn.

        Returns:
            Whatever fn returns.

        Raises:
            HFClientError: After _MAX_RETRIES failed attempts.
        """
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY * attempt)
        raise HFClientError(
            f"HF API call failed after {_MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc


# Module-level singleton
_hf_client: HFClient | None = None


def get_hf_client() -> HFClient:
    """Return the module-level HFClient singleton, creating it if needed."""
    global _hf_client  # noqa: PLW0603
    if _hf_client is None:
        _hf_client = HFClient()
    return _hf_client
