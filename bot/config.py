from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Config:
    bot_token: str
    lms_api_base_url: str
    lms_api_key: str
    llm_api_key: str
    llm_api_base_url: str
    llm_api_model: str

    @classmethod
    def load(cls) -> "Config":
        base_dir = Path(__file__).resolve().parent
        env_path = base_dir.parent / ".env.bot.secret"
        load_env_file(env_path)

        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            lms_api_base_url=os.getenv("LMS_API_BASE_URL", ""),
            lms_api_key=os.getenv("LMS_API_KEY", ""),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_api_base_url=os.getenv("LLM_API_BASE_URL", ""),
            llm_api_model=os.getenv("LLM_API_MODEL", ""),
        )
