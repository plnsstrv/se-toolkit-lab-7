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
    timeout: float = 15.0

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            ) as client:
                response = await client.get(
                    self._url(path),
                    headers=self._headers(),
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise BackendError(str(exc)) from exc

    async def get_items(self) -> list[dict[str, Any]]:
        data = await self.get_json("/items/")
        return data if isinstance(data, list) else []

    async def get_pass_rates(self, lab: str) -> list[dict[str, Any]]:
        data = await self.get_json("/analytics/pass-rates", params={"lab": lab})
        return data if isinstance(data, list) else []

    async def get_learners(self) -> list[dict[str, Any]]:
        data = await self.get_json("/learners/")
        return data if isinstance(data, list) else []

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
        labs = [item for item in items if item.get("type") == "lab"]
        labs.sort(key=lambda item: str(item.get("title", "")))
        return labs

    async def get_lab_titles(self) -> list[str]:
        labs = await self.get_labs()
        return [str(lab.get("title", "Untitled lab")) for lab in labs]

    async def get_scores_for_lab(self, lab: str) -> list[dict[str, Any]]:
        return await self.get_pass_rates(lab)

    async def get_enrollment_count(self) -> int:
        learners = await self.get_learners()
        return len(learners)

    async def get_lowest_pass_rate_lab(self) -> dict[str, Any]:
        labs = await self.get_labs()
        best_row: dict[str, Any] | None = None

        for lab in labs:
            title = str(lab.get("title", ""))
            prefix = title.split("—", 1)[0].strip().replace("–", "").strip()
            parts = prefix.split()
            if len(parts) >= 2 and parts[1].isdigit():
                lab_id = f"lab-{int(parts[1]):02d}"
            else:
                continue

            rows = await self.get_scores_for_lab(lab_id)
            for row in rows:
                avg_score = row.get("avg_score")
                if not isinstance(avg_score, (int, float)):
                    continue

                candidate = {
                    "lab": lab_id,
                    "task": row.get("task", "Unknown task"),
                    "avg_score": float(avg_score),
                }

                if best_row is None or candidate["avg_score"] < best_row["avg_score"]:
                    best_row = candidate

        return best_row or {}

    async def get_highest_pass_rate_lab(self) -> dict[str, Any]:
        labs = await self.get_labs()
        best_row: dict[str, Any] | None = None

        for lab in labs:
            title = str(lab.get("title", ""))
            prefix = title.split("—", 1)[0].strip().replace("–", "").strip()
            parts = prefix.split()
            if len(parts) >= 2 and parts[1].isdigit():
                lab_id = f"lab-{int(parts[1]):02d}"
            else:
                continue

            rows = await self.get_scores_for_lab(lab_id)
            for row in rows:
                avg_score = row.get("avg_score")
                if not isinstance(avg_score, (int, float)):
                    continue

                candidate = {
                    "lab": lab_id,
                    "task": row.get("task", "Unknown task"),
                    "avg_score": float(avg_score),
                }

                if best_row is None or candidate["avg_score"] > best_row["avg_score"]:
                    best_row = candidate

        return best_row or {}
