from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class LLMError(Exception):
    pass


@dataclass
class LLMClient:
    base_url: str
    api_key: str
    model: str
    timeout: float = 40.0

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_with_tools(
        self,
        user_text: str,
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._url("/chat/completions"),
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise LLMError(str(exc)) from exc
