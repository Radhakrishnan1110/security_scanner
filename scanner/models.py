from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import ModelConfig


class PromptBlockedError(RuntimeError):
    """The provider declined to process a prompt before generating a response."""


class LanguageModel(Protocol):
    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return a model response for a security-scanning prompt."""


def _post_json(request: Request, timeout_seconds: int, provider: str) -> dict:
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            retry_after = error.headers.get("Retry-After") if error.headers else None
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (2**attempt)
            time.sleep(min(delay, 60))
        except (TimeoutError, socket.timeout, URLError) as error:
            if attempt == 2:
                raise RuntimeError(f"{provider} request timed out or could not reach the service after 3 attempts: {error}") from error
            time.sleep(5 * (2**attempt))
    raise AssertionError("Unreachable")


@dataclass
class OpenAICompatibleModel:
    config: ModelConfig

    @property
    def name(self) -> str:
        return self.config.model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.config.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        request = Request(
            f"{self.config.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.config.api_key()}",
                "Content-Type": "application/json",
                "User-Agent": "apk-security-scanner/0.1 (authorized defensive static review)",
            },
            method="POST",
        )
        try:
            body = _post_json(request, self.config.timeout_seconds, "Model")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Model request failed ({error.code}): {detail}") from error
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected model response: {body}") from error


@dataclass
class GeminiModel:
    config: ModelConfig

    @property
    def name(self) -> str:
        return self.config.model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            }
        ).encode("utf-8")
        url = f"{self.config.base_url}/models/{quote(self.config.model, safe='')}:generateContent?key={quote(self.config.api_key(), safe='')}"
        request = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            body = _post_json(request, self.config.timeout_seconds, "Gemini")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini request failed ({error.code}): {detail}") from error
        if "promptFeedback" in body and not body.get("candidates"):
            reason = body["promptFeedback"].get("blockReason", "unspecified")
            raise PromptBlockedError(f"Gemini blocked this prompt: {reason}")
        try:
            return "".join(part["text"] for part in body["candidates"][0]["content"]["parts"] if "text" in part)
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected Gemini response: {body}") from error


def create_model(config: ModelConfig) -> LanguageModel:
    if config.provider == "openai_compatible":
        return OpenAICompatibleModel(config)
    if config.provider == "gemini":
        return GeminiModel(config)
    raise ValueError(f"Unsupported model provider: {config.provider}")
