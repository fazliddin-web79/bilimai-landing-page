import re
from typing import Any, Dict

from bot.constants import CONSENT_TEXT


def clean_text(value: str, max_length: int = 120) -> str:
    text = " ".join(value.strip().split())
    if len(text) > max_length:
        text = text[:max_length].strip()
    return text


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("8") and len(digits) == 10:
        return "+998" + digits[1:]
    if len(digits) == 9:
        return "+998" + digits
    if value.strip().startswith("+") and 9 <= len(digits) <= 15:
        return "+" + digits
    raise ValueError("Telefon raqam noto'g'ri. Masalan: +998901234567")


def registration_summary(data: Dict[str, Any]) -> str:
    username = data.get("telegram_username") or "-"
    attended = "Keldi" if int(data.get("attended", 0)) else "Kelmagan"
    return (
        f"Kod: {data.get('participant_code', '-')}\n"
        f"Ota-ona: {data.get('parent_full_name', '-')}\n"
        f"Telefon: {data.get('phone', '-')}\n"
        f"O'quvchi: {data.get('student_full_name', '-')}\n"
        f"Sinf: {data.get('grade', '-')}\n"
        f"Maktab: {data.get('current_school', '-')}\n"
        f"Mahalla/hudud: {data.get('neighborhood', '-')}\n"
        f"Olimpiada manzili: {data.get('olympiad_location', '-')}\n"
        f"Manba: {data.get('source', '-')}\n"
        f"Telegram: {data.get('telegram_id', '-')} (@{username})\n"
        f"Holat: {attended}\n"
        f"Sana: {data.get('created_at', '-')}"
    )


def confirmation_text(data: Dict[str, Any]) -> str:
    return (
        "Ma'lumotlarni tekshiring:\n\n"
        f"Ota-ona: {data['parent_full_name']}\n"
        f"Telefon: {data['phone']}\n"
        f"O'quvchi: {data['student_full_name']}\n"
        f"Sinf: {data['grade']}\n"
        f"Maktab: {data['current_school']}\n"
        f"Mahalla/hudud: {data['neighborhood']}\n"
        f"Olimpiada manzili: {data['olympiad_location']}\n"
        f"Reklama manbasi: {data['source']}\n\n"
        f"{CONSENT_TEXT}"
    )
