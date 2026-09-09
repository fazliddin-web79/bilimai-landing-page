import re
from typing import Any, Dict, List, Tuple

from bot.constants import (
    ANSWER_OPTIONS,
    CONSENT_TEXT,
    OLYMPIAD_LOCATIONS,
    OLYMPIAD_SCHEDULES,
    TEST_QUESTION_COUNT,
)


def clean_text(value: str, max_length: int = 120) -> str:
    text = " ".join(value.strip().split())
    if len(text) > max_length:
        text = text[:max_length].strip()
    return text


def clean_multiline_text(value: str, max_length: int = 3500) -> str:
    lines = [" ".join(line.strip().split()) for line in value.strip().splitlines()]
    text = "\n".join(line for line in lines if line)
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


def parse_answer_text(value: str, total: int = TEST_QUESTION_COUNT) -> str:
    compact = re.sub(r"[\s,.;:_\-|/]+", "", value.upper())
    position = 0
    answers: List[str] = []
    for question_number in range(1, total + 1):
        expected_number = str(question_number)
        if not compact.startswith(expected_number, position):
            raise ValueError(
                f"Javob formati noto'g'ri. {question_number}-savol uchun "
                f"{question_number}A ko'rinishida yozing."
            )
        position += len(expected_number)
        if position >= len(compact) or compact[position] not in ANSWER_OPTIONS:
            raise ValueError(
                f"{question_number}-savol javobi A, B, C yoki D bo'lishi kerak."
            )
        answers.append(compact[position])
        position += 1
    if position != len(compact):
        raise ValueError("Javobda ortiqcha belgi bor. Namuna: 1A2B3C...30D")
    return "".join(
        f"{index}{answer}" for index, answer in enumerate(answers, start=1)
    )


def score_answers(submitted: str, answer_key: str) -> Tuple[int, List[int]]:
    submitted_answers = answers_to_list(submitted)
    key_answers = answers_to_list(answer_key)
    wrong_questions: List[int] = []
    correct = 0
    for index, (submitted_answer, key_answer) in enumerate(
        zip(submitted_answers, key_answers), start=1
    ):
        if submitted_answer == key_answer:
            correct += 1
        else:
            wrong_questions.append(index)
    return correct, wrong_questions


def answers_to_list(value: str) -> List[str]:
    normalized = parse_answer_text(value)
    return re.findall(r"\d+([ABCD])", normalized)


def normalize_location(value: str) -> str:
    normalized = clean_text(value, 40).casefold()
    for location in OLYMPIAD_LOCATIONS:
        if normalized == location.casefold():
            return location
    raise ValueError("Bunday olimpiada hududi topilmadi.")


def olympiad_schedule_text(location: str) -> str:
    schedule = OLYMPIAD_SCHEDULES.get(location)
    if not schedule:
        return ""
    return f"\nOlimpiada vaqti: {schedule}"


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
        f"Olimpiada manzili: {data.get('olympiad_location', '-')}"
        f"{olympiad_schedule_text(data.get('olympiad_location', ''))}\n"
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
        f"Olimpiada manzili: {data['olympiad_location']}"
        f"{olympiad_schedule_text(data['olympiad_location'])}\n"
        f"Reklama manbasi: {data['source']}\n\n"
        f"{CONSENT_TEXT}"
    )
