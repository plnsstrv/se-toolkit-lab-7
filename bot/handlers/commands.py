from __future__ import annotations


def handle_command(text: str) -> str:
    command = (text or "").strip()

    if not command:
        return "Empty command. Try /start or /help."

    if command == "/start":
        return (
            "Welcome to the SE Toolkit bot.\n"
            "Available commands: /start, /help, /health, /labs."
        )

    if command == "/help":
        return (
            "Available commands:\n"
            "/start - welcome message\n"
            "/help - show this help\n"
            "/health - backend health placeholder\n"
            "/labs - list labs placeholder"
        )

    if command == "/health":
        return "Backend status check is not implemented yet."

    if command == "/labs":
        return "Labs list is not implemented yet."

    return f"Unknown command: {command}\nTry /help."
