"""DeepSeek provider via Anthropic-compatible API using requests."""
import json
import os
from typing import List, Optional

import requests

from models.quintuple import Quintuple
from prompts.templates import EXTRACT_SYSTEM_PROMPT, build_extract_prompt
from .base import BaseLLM


class DeepSeekLLM(BaseLLM):
    """DeepSeek API adapter using Anthropic-compatible endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN", ""
        )
        self.base_url = base_url or os.environ.get(
            "ANTHROPIC_BASE_URL",
            "https://api.deepseek.com/anthropic",
        )
        self.model = model or os.environ.get(
            "ANTHROPIC_MODEL", "deepseek-v4-pro[1m]"
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def generate(self, system_prompt: str, user_message: str) -> str:
        """Send a chat completion request and return the text response."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/messages",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            # Anthropic format: content[0].text
            content = data.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            # OpenAI format fallback: choices[0].message.content
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except requests.RequestException as e:
            print(f"[DeepSeekLLM] API error: {e}")
            return ""

    def extract_quintuples(
        self,
        text: str,
        syntactic_hints: Optional[dict] = None,
    ) -> List[Quintuple]:
        prompt = build_extract_prompt(text, syntactic_hints)
        raw = self.generate(EXTRACT_SYSTEM_PROMPT, prompt)
        return self._parse_response(raw, text)

    def _parse_response(
        self, raw: str, source_text: str
    ) -> List[Quintuple]:
        """Parse LLM JSON response into Quintuple list."""
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
            else:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    data = [json.loads(raw[start:end])]
                else:
                    return []
            return [
                Quintuple.from_dict(
                    item, source_text=source_text, confidence=0.9
                )
                for item in data
            ]
        except (json.JSONDecodeError, KeyError):
            return []
