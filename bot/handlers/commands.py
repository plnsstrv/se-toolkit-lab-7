from __future__ import annotations

from handlers.common import format_unknown_command
from services import BackendClient, BackendError


def _normalize_lab_id(raw: str) -> str | None:
    value = raw.strip().lower()
    if not value.startswith("lab-"):
        return None

    suffix = value.removeprefix("lab-")
    if not suffix.isdigit():
        return None

    return f"lab-{int(suffix):02d}"


async def handle_command(text: str, backend: BackendClient) -> str:
    command = (text or "").strip()

    if not command:
        return "Empty command. Try /start or /help."

    if command == "/start":
        return (
            "Welcome to the SE Toolkit bot.\n"
            "Available commands: /start, /help, /health, /labs, /scores <lab-id>."
        )

    if command == "/help":
        return (
            "Available commands:\n"
            "/start - welcome message\n"
            "/help - show this help\n"
            "/health - backend health and items count\n"
            "/labs - list available labs from backend\n"
            "/scores <lab-id> - show per-task averages and attempts, e.g. /scores lab-04"
        )

    if command == "/health":
        try:
            summary = await backend.get_health_summary()
            return (
                f"Backend health: {summary.get('status', 'unknown')}. "
                f"Items: {summary.get('items_count', 0)}. "
                f"Learners: {summary.get('learners_count', 0)}."
            )
        except BackendError as exc:
            return f"Backend health: error. {exc}"

    if command == "/labs":
        try:
            titles = await backend.get_lab_titles()
            if not titles:
                return "No labs found in backend data."
            return "Available labs:\n" + "\n".join(f"- {title}" for title in titles)
        except BackendError as exc:
            return f"Could not load labs from backend: {exc}"

    if command.startswith("/scores"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            return "Usage: /scores lab-04"

        lab_id = _normalize_lab_id(parts[1])
        if lab_id is None:
            return "Invalid lab id. Use format like /scores lab-04"

        try:
            rows = await backend.get_scores_for_lab(lab_id)
            if not rows:
                return f"No score data found for {lab_id}."

            lines = [f"Scores for {lab_id}:"]
            for row in rows:
                task = row.get("task", "Unknown task")
                avg_score = row.get("avg_score", 0)
                attempts = row.get("attempts", 0)
                lines.append(f"- {task}: {avg_score}% average, {attempts} attempts")
            return "\n".join(lines)
        except BackendError as exc:
            return f"Could not load scores for {lab_id}: {exc}"

    return format_unknown_command(command)
