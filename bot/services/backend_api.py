from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class BackendError(Exception):
    pass


@dataclass
class BackendClient:
    base_url: str
    api_key: str
    timeout: float = 20.0

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self._url(path)
        print(f"[api] Calling GET {url}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self._headers(), params=params)
                print(f"[api] Status: {response.status_code}")
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise BackendError(str(exc)) from exc

    async def post_json(self, path: str, json_body: dict[str, Any] | None = None) -> Any:
        url = self._url(path)
        print(f"[api] Calling POST {url}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.post(url, headers=self._headers(), json=json_body or {})
                print(f"[api] Status: {response.status_code}")
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise BackendError(str(exc)) from exc

    # Task 3 exact backend wrappers

    async def get_items(self) -> list[dict[str, Any]]:
        data = await self.get_json("/items/")
        return data if isinstance(data, list) else []

    async def get_learners(self) -> list[dict[str, Any]]:
        data = await self.get_json("/learners/")
        return data if isinstance(data, list) else []

    async def get_scores(self, lab: str) -> list[dict[str, Any]]:
        data = await self.get_json("/analytics/scores", params={"lab": lab})
        return data if isinstance(data, list) else []

    async def get_pass_rates(self, lab: str) -> list[dict[str, Any]]:
        data = await self.get_json("/analytics/pass-rates", params={"lab": lab})
        return data if isinstance(data, list) else []

    async def get_timeline(self, lab: str) -> list[dict[str, Any]]:
        data = await self.get_json("/analytics/timeline", params={"lab": lab})
        return data if isinstance(data, list) else []

    async def get_groups(self, lab: str) -> list[dict[str, Any]]:
        data = await self.get_json("/analytics/groups", params={"lab": lab})
        return data if isinstance(data, list) else []

    async def get_top_learners(self, lab: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if lab:
            params["lab"] = lab
        data = await self.get_json("/analytics/top-learners", params=params)
        return data if isinstance(data, list) else []

    async def get_completion_rate(self, lab: str) -> Any:
        return await self.get_json("/analytics/completion-rate", params={"lab": lab})

    async def trigger_sync(self) -> Any:
        return await self.post_json("/pipeline/sync", json_body={})

    # Command compatibility helpers

    async def get_health_summary(self) -> dict[str, Any]:
        items = await self.get_items()
        learners = await self.get_learners()
        return {
            "status": "ok",
            "items_count": len(items),
            "learners_count": len(learners),
        }

    async def get_labs(self) -> list[dict[str, Any]]:
        items = await self.get_items()
        result: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title", "")).strip()
            kind = str(item.get("type", "")).strip().lower()
            if kind == "lab":
                result.append(item)
                continue
            if title.lower().startswith("lab ") or title.lower().startswith("lab-"):
                result.append(item)
        return result

    async def get_lab_titles(self) -> list[str]:
        labs = await self.get_labs()
        titles: list[str] = []
        for lab in labs:
            title = str(lab.get("title", "")).strip()
            if title:
                titles.append(title)
        return titles

    async def get_scores_for_lab(self, lab: str) -> list[dict[str, Any]]:
        return await self.get_pass_rates(lab)

    async def get_enrollment_count(self) -> int:
        learners = await self.get_learners()
        return len(learners)
