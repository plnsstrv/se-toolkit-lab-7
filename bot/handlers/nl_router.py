from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from services import BackendClient, LLMClient, LLMError

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]

SYSTEM_PROMPT = """
You are an LMS analytics assistant.

Use tools for every factual LMS question. Never answer from memory when tools can provide the data.

Available tools:
- get_items: list all labs and tasks from the backend
- get_learners: list learners and enrollment data
- get_scores: score distribution for a lab
- get_pass_rates: per-task pass-rate / average-score data for a lab
- get_timeline: timeline data for a lab
- get_groups: group performance for a lab
- get_top_learners: top learners globally or for a lab
- get_completion_rate: completion percentage for a lab
- trigger_sync: sync data from the pipeline

Routing guidance:
- "what labs are available" -> get_items
- "show me scores for lab 4" -> get_scores with lab="lab-04"
- "how many students are enrolled" -> get_learners
- "which group is doing best in lab 3" -> get_groups with lab="lab-03"
- "which lab has the lowest pass rate" -> get_items, then get_pass_rates for labs, then compare
- "who are the top 5 students" -> get_top_learners with limit=5
- "sync the data" -> trigger_sync

Rules:
- Do not ask follow-up questions if the tools already allow an answer.
- Do not ask for a lab when answering "top 5 students" unless the user explicitly asked for a specific lab.
- Avoid repeating the same tool call with the same arguments.
- Use concrete backend data in the final answer: lab names, task names, numbers, group names, learner names, scores, percentages, attempts.
- For greetings or nonsense, answer briefly without tools.
""".strip()


def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_items",
                "description": "List all labs and tasks from the backend.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_learners",
                "description": "List enrolled learners and enrollment data.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_scores",
                "description": "Get score distribution for a lab like lab-04.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {"type": "string", "description": "Lab id like lab-04"}
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pass_rates",
                "description": "Get per-task pass-rate or average-score data for a lab like lab-04.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {"type": "string", "description": "Lab id like lab-04"}
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_timeline",
                "description": "Get timeline or submissions-over-time data for a lab like lab-04.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {"type": "string", "description": "Lab id like lab-04"}
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_groups",
                "description": "Get group performance for a lab like lab-03.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {"type": "string", "description": "Lab id like lab-03"}
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_learners",
                "description": "Get the top learners globally across all labs, or for a specific lab if lab is provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {"type": "string", "description": "Optional lab id like lab-04"},
                        "limit": {"type": "integer", "description": "Number of learners to return", "default": 5},
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_completion_rate",
                "description": "Get completion percentage for a lab like lab-05.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {"type": "string", "description": "Lab id like lab-05"}
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "trigger_sync",
                "description": "Trigger backend sync / pipeline refresh.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]


def _is_greeting_or_nonsense(text: str) -> bool:
    lowered = " ".join((text or "").lower().strip().split())
    if not lowered:
        return True
    greetings = {
        "hello",
        "hi",
        "hey",
        "greetings",
        "good morning",
        "good afternoon",
        "good evening",
    }
    if lowered in greetings:
        return True
    if lowered in {"asdfgh", "qwerty", "zxcvbn", "aaaaa", "bbbbbb"}:
        return True
    return False


def _normalize_lab_id(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip().lower().replace("_", "-")
    if not text:
        return None

    if text.startswith("lab-"):
        suffix = text[4:]
        if suffix.isdigit():
            return f"lab-{int(suffix):02d}"
        return None

    if text.startswith("lab"):
        suffix = text[3:]
        if suffix.isdigit():
            return f"lab-{int(suffix):02d}"
        return None

    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return f"lab-{int(digits):02d}"

    return None


def _safe_int(value: Any, default: int = 5) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    if parsed < 1:
        return 1
    if parsed > 20:
        return 20
    return parsed


def _normalize_tool_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name in {"get_scores", "get_pass_rates", "get_timeline", "get_groups", "get_completion_rate"}:
        lab = _normalize_lab_id(args.get("lab"))
        if not lab:
            raise ValueError("lab is required and must look like lab-04")
        return {"lab": lab}

    if name == "get_top_learners":
        normalized: dict[str, Any] = {"limit": _safe_int(args.get("limit", 5), 5)}
        lab = _normalize_lab_id(args.get("lab"))
        if lab:
            normalized["lab"] = lab
        return normalized

    if name in {"get_items", "get_learners", "trigger_sync"}:
        return {}

    return args


async def _tool_get_items(_: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_items()


async def _tool_get_learners(_: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_learners()


async def _tool_get_scores(args: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_scores(args["lab"])


async def _tool_get_pass_rates(args: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_pass_rates(args["lab"])


async def _tool_get_timeline(args: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_timeline(args["lab"])


async def _tool_get_groups(args: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_groups(args["lab"])


async def _tool_get_top_learners(args: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_top_learners(lab=args.get("lab"), limit=args.get("limit", 5))


async def _tool_get_completion_rate(args: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.get_completion_rate(args["lab"])


async def _tool_trigger_sync(_: dict[str, Any], backend: BackendClient) -> Any:
    return await backend.trigger_sync()


def build_tool_handlers(backend: BackendClient) -> dict[str, ToolHandler]:
    return {
        "get_items": lambda args: _tool_get_items(args, backend),
        "get_learners": lambda args: _tool_get_learners(args, backend),
        "get_scores": lambda args: _tool_get_scores(args, backend),
        "get_pass_rates": lambda args: _tool_get_pass_rates(args, backend),
        "get_timeline": lambda args: _tool_get_timeline(args, backend),
        "get_groups": lambda args: _tool_get_groups(args, backend),
        "get_top_learners": lambda args: _tool_get_top_learners(args, backend),
        "get_completion_rate": lambda args: _tool_get_completion_rate(args, backend),
        "trigger_sync": lambda args: _tool_trigger_sync(args, backend),
    }


def _extract_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices", [])
    if not choices:
        return {}

    message = choices[0].get("message", {}) or {}

    if message.get("function_call") and not message.get("tool_calls"):
        message["tool_calls"] = [
            {
                "id": "legacy-tool-call-1",
                "type": "function",
                "function": message["function_call"],
            }
        ]

    return message


def _parse_tool_arguments(raw_arguments: Any) -> dict[str, Any]:
    if raw_arguments is None:
        return {}
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str) or not raw_arguments.strip():
        return {}
    try:
        parsed = json.loads(raw_arguments)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _tool_result_summary(name: str, result: Any) -> str:
    if isinstance(result, list):
        return f"{name}: {len(result)} row(s)"
    if isinstance(result, dict):
        return f"{name}: {len(result)} field(s)"
    return f"{name}: {str(result)[:120]}"


async def route_natural_language(
    text: str,
    llm: LLMClient,
    backend: BackendClient,
) -> str:
    user_text = (text or "").strip()
    print(f"[route] Input: {user_text}")

    if _is_greeting_or_nonsense(user_text):
        return (
            "Hello! I can help with labs, scores, pass rates, groups, top learners, "
            "completion rates, timelines, and sync."
        )

    tools = get_tool_schemas()
    handlers = build_tool_handlers(backend)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    seen_calls: set[str] = set()
    tool_results_count = 0

    try:
        for iteration in range(1, 8):
            print(f"[route] Iteration {iteration}")
            response = await llm.chat(messages=messages, tools=tools)
            message = _extract_message(response)
            content = str(message.get("content") or "")
            tool_calls = message.get("tool_calls") or []

            assistant_message: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            messages.append(assistant_message)

            if not tool_calls:
                final_text = content.strip()
                if final_text:
                    print(f"[llm] Final answer: {final_text[:120]}...")
                    return final_text
                break

            print(f"[tool] LLM called {len(tool_calls)} tool(s): {[tc.get('function', {}).get('name') for tc in tool_calls]}")

            for tool_call in tool_calls:
                function = tool_call.get("function", {}) or {}
                tool_name = str(function.get("name", "")).strip()
                parsed_args = _parse_tool_arguments(function.get("arguments", "{}"))
                normalized_args = _normalize_tool_args(tool_name, parsed_args)

                print(f"[tool] Executing: {tool_name}({normalized_args})")

                signature = json.dumps(
                    {"name": tool_name, "args": normalized_args},
                    ensure_ascii=False,
                    sort_keys=True,
                )

                if signature in seen_calls:
                    result: Any = {
                        "notice": "This tool call was already executed with the same arguments. Use previous results and answer the user."
                    }
                else:
                    seen_calls.add(signature)
                    handler = handlers[tool_name]
                    result = await handler(normalized_args)

                print(f"[tool] Result: {_tool_result_summary(tool_name, result)}")

                tool_call_id = str(tool_call.get("id") or f"tool-call-{tool_results_count + 1}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
                tool_results_count += 1

            print(f"[summary] Fed {tool_results_count} tool result(s) back to LLM")

        if tool_results_count > 0:
            final_response = await llm.chat(
                messages=messages + [
                    {
                        "role": "user",
                        "content": "Answer the original question now using the tool results above. Include concrete backend data and numbers.",
                    }
                ],
                tools=None,
            )
            final_message = _extract_message(final_response)
            final_text = str(final_message.get("content") or "").strip()
            if final_text:
                print(f"[llm] Final answer: {final_text[:120]}...")
                return final_text

    except LLMError as exc:
        print(f"[llm] Error: {exc}")
        return "I'm unable to connect to the AI service right now. Please try again later."
    except Exception as exc:
        print(f"[route] Error: {exc}")
        return f"Routing error: {exc}"

    return (
        "I could not answer that yet. Ask me about labs, scores, pass rates, groups, "
        "top learners, completion rates, timelines, or sync."
    )
