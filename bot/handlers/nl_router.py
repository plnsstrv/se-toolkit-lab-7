from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from services import BackendClient, LLMClient, LLMError

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_health_summary",
                "description": "Get backend health summary with counts of items and learners.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_labs",
                "description": "List real lab titles available in backend.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_lab_scores",
                "description": "Get per-task score information for a specific lab like lab-04.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab id in format lab-01, lab-02, lab-03, etc.",
                        }
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_enrollment_count",
                "description": "Get total number of enrolled learners or students.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_lowest_pass_rate_lab",
                "description": "Find the lab with the lowest average pass rate or score.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_highest_pass_rate_lab",
                "description": "Find the lab with the highest average pass rate or score.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "count_items",
                "description": "Count total items stored in backend.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_lab_titles",
                "description": "Get plain list of lab titles from backend.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pass_rates_overview",
                "description": "Get pass rate overview from analytics endpoint.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_learners_preview",
                "description": "Get count and a short preview of learners data.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]


async def _tool_get_health_summary(_: dict[str, Any], backend: BackendClient) -> str:
    summary = await backend.get_health_summary()
    return (
        f"Backend health: {summary.get('status', 'unknown')}. "
        f"Items: {summary.get('items_count', 0)}. "
        f"Learners: {summary.get('learners_count', 0)}."
    )


async def _tool_list_labs(_: dict[str, Any], backend: BackendClient) -> str:
    labs = await backend.get_lab_titles()
    if not labs:
        return "No labs found."
    return "Available labs:\n" + "\n".join(f"- {lab}" for lab in labs)


async def _tool_get_lab_scores(args: dict[str, Any], backend: BackendClient) -> str:
    lab = str(args.get("lab", "")).strip().lower()
    rows = await backend.get_scores_for_lab(lab)
    if not rows:
        return f"No score data found for {lab}."

    lines = [f"Scores for {lab}:"]
    for row in rows:
        task = row.get("task", "Unknown task")
        avg_score = row.get("avg_score", 0)
        attempts = row.get("attempts", 0)
        lines.append(f"- {task}: {avg_score}% average, {attempts} attempts")
    return "\n".join(lines)


async def _tool_get_enrollment_count(_: dict[str, Any], backend: BackendClient) -> str:
    count = await backend.get_enrollment_count()
    return f"Total enrolled learners: {count}."


async def _tool_get_lowest_pass_rate_lab(_: dict[str, Any], backend: BackendClient) -> str:
    row = await backend.get_lowest_pass_rate_lab()
    if not row:
        return "No pass rate data available."
    return (
        f"Lowest pass rate: {row.get('lab', 'unknown lab')} - "
        f"{row.get('task', 'unknown task')} - {row.get('avg_score', 0)}%."
    )


async def _tool_get_highest_pass_rate_lab(_: dict[str, Any], backend: BackendClient) -> str:
    row = await backend.get_highest_pass_rate_lab()
    if not row:
        return "No pass rate data available."
    return (
        f"Highest pass rate: {row.get('lab', 'unknown lab')} - "
        f"{row.get('task', 'unknown task')} - {row.get('avg_score', 0)}%."
    )


async def _tool_count_items(_: dict[str, Any], backend: BackendClient) -> str:
    items = await backend.get_items()
    return f"Total backend items: {len(items)}."


async def _tool_get_lab_titles(_: dict[str, Any], backend: BackendClient) -> str:
    titles = await backend.get_lab_titles()
    return "Lab titles:\n" + "\n".join(f"- {title}" for title in titles)


async def _tool_get_pass_rates_overview(_: dict[str, Any], backend: BackendClient) -> str:
    labs = await backend.get_labs()
    lines = ["Pass-rate overview:"]
    count = 0

    for lab in labs:
        title = str(lab.get("title", ""))
        prefix = title.split("—", 1)[0].strip().replace("–", "").strip()
        parts = prefix.split()
        if len(parts) < 2 or not parts[1].isdigit():
            continue

        lab_id = f"lab-{int(parts[1]):02d}"
        rows = await backend.get_scores_for_lab(lab_id)
        for row in rows[:2]:
            lines.append(
                f"- {lab_id} / {row.get('task', 'unknown task')}: "
                f"{row.get('avg_score', 0)}% average, {row.get('attempts', 0)} attempts"
            )
            count += 1
            if count >= 5:
                return "\n".join(lines)

    return "\n".join(lines) if count else "No pass-rate overview available."


async def _tool_get_learners_preview(_: dict[str, Any], backend: BackendClient) -> str:
    learners = await backend.get_learners()
    preview = learners[:3]
    return f"Learners total: {len(learners)}. Preview rows: {preview}"


def build_tool_handlers(backend: BackendClient) -> dict[str, ToolHandler]:
    return {
        "get_health_summary": lambda args: _tool_get_health_summary(args, backend),
        "list_labs": lambda args: _tool_list_labs(args, backend),
        "get_lab_scores": lambda args: _tool_get_lab_scores(args, backend),
        "get_enrollment_count": lambda args: _tool_get_enrollment_count(args, backend),
        "get_lowest_pass_rate_lab": lambda args: _tool_get_lowest_pass_rate_lab(args, backend),
        "get_highest_pass_rate_lab": lambda args: _tool_get_highest_pass_rate_lab(args, backend),
        "count_items": lambda args: _tool_count_items(args, backend),
        "get_lab_titles": lambda args: _tool_get_lab_titles(args, backend),
        "get_pass_rates_overview": lambda args: _tool_get_pass_rates_overview(args, backend),
        "get_learners_preview": lambda args: _tool_get_learners_preview(args, backend),
    }


def _extract_tool_call(response: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    choices = response.get("choices", [])
    if not choices:
        return None, {}

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])
    if not tool_calls:
        return None, {}

    function_call = tool_calls[0].get("function", {})
    name = function_call.get("name")
    raw_arguments = function_call.get("arguments", "{}")

    try:
        args = json.loads(raw_arguments) if raw_arguments else {}
    except json.JSONDecodeError:
        args = {}

    return name, args


def _extract_lab_id(text: str) -> str | None:
    lowered = text.lower().replace("-", " ").replace("_", " ")
    tokens = lowered.split()

    for token in tokens:
        if token.isdigit():
            n = int(token)
            if 1 <= n <= 20:
                return f"lab-{n:02d}"

    for token in tokens:
        if token.startswith("lab") and len(token) > 3:
            suffix = token[3:]
            if suffix.isdigit():
                n = int(suffix)
                if 1 <= n <= 20:
                    return f"lab-{n:02d}"

    return None


def _fallback_tool_choice(text: str) -> tuple[str, dict[str, Any]] | None:
    lowered = text.lower()

    if "lowest" in lowered and "pass" in lowered:
        return "get_lowest_pass_rate_lab", {}

    if "highest" in lowered and "pass" in lowered:
        return "get_highest_pass_rate_lab", {}

    if "score" in lowered:
        lab_id = _extract_lab_id(lowered)
        if lab_id:
            return "get_lab_scores", {"lab": lab_id}
        return "get_pass_rates_overview", {}

    if "student" in lowered or "enrolled" in lowered or "learner" in lowered:
        return "get_enrollment_count", {}

    if "lab" in lowered and ("available" in lowered or "list" in lowered or "what" in lowered):
        return "list_labs", {}

    if "sync" in lowered or "load" in lowered or "data" in lowered:
        return "get_health_summary", {}

    return None


async def route_natural_language(
    text: str,
    llm: LLMClient,
    backend: BackendClient,
) -> str:
    tools = get_tool_schemas()
    handlers = build_tool_handlers(backend)

    system_prompt = (
        "You are a routing assistant for an LMS bot. "
        "Always decide which tool best answers the user's request. "
        "Never answer from memory when a tool can provide real data. "
        "For labs, scores, enrollment, backend health, pass rates, and comparisons, call exactly one tool."
    )

    tool_name: str | None = None
    args: dict[str, Any] = {}

    try:
        response = await llm.chat_with_tools(
            user_text=text,
            tools=tools,
            system_prompt=system_prompt,
        )
        tool_name, args = _extract_tool_call(response)
    except LLMError:
        tool_name = None
        args = {}

    if not tool_name:
        fallback = _fallback_tool_choice(text)
        if fallback is not None:
            tool_name, args = fallback

    if not tool_name:
        return (
            "I could not understand that request. "
            "Try asking about available labs, scores for a lab, enrollment, or pass rates."
        )

    handler = handlers.get(tool_name)
    if handler is None:
        return f"Tool not implemented: {tool_name}"

    try:
        result = await handler(args)
    except Exception:
        return (
            "I could not complete that request. "
            "Try asking about available labs, scores for a lab, enrollment, or pass rates."
        )

    if tool_name == "get_health_summary" and ("sync" in text.lower() or "load" in text.lower()):
        return f"Sync check complete. {result}"

    return result
