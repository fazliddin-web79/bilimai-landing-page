from typing import Any, Dict, Optional

from bot.constants import UNKNOWN_SOURCE
from bot.database import RegistrationInput


def build_registration_input(
    telegram_id: int,
    telegram_username: Optional[str],
    state_data: Dict[str, Any],
) -> RegistrationInput:
    return RegistrationInput(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        parent_full_name=state_data["parent_full_name"],
        phone=state_data["phone"],
        student_full_name=state_data["student_full_name"],
        grade=state_data["grade"],
        current_school=state_data["current_school"],
        neighborhood=state_data["neighborhood"],
        olympiad_location=state_data["olympiad_location"],
        source=state_data.get("source", UNKNOWN_SOURCE),
    )
