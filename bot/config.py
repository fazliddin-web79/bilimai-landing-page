import os
from dataclasses import dataclass
from typing import Set

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    database_path: str
    admin_ids: Set[int]

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        telegram_token = (
            os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        ).strip()
        admin_ids = parse_admin_ids(os.getenv("ADMIN_IDS", ""))

        if not telegram_token:
            raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan.")

        return cls(
            telegram_bot_token=telegram_token,
            database_path=os.getenv("DATABASE_PATH", "bot.db").strip(),
            admin_ids=admin_ids,
        )


def parse_admin_ids(raw_value: str) -> Set[int]:
    ids: Set[int] = set()
    for item in raw_value.replace(";", ",").split(","):
        value = item.strip()
        if not value:
            continue
        try:
            ids.add(int(value))
        except ValueError as exc:
            raise RuntimeError("ADMIN_IDS faqat Telegram ID raqamlaridan iborat bo'lishi kerak.") from exc
    return ids
