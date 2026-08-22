import asyncio
import tempfile
from pathlib import Path
from typing import Callable, Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, Message

from bot.config import Config
from bot.constants import GRADES, OLYMPIAD_LOCATIONS, TEST_QUESTION_COUNT
from bot.database import Database
from bot.utils import (
    clean_text,
    normalize_phone,
    parse_answer_text,
    registration_summary,
    score_answers,
)

router = Router()

EDIT_FIELDS = {
    "parent": "parent_full_name",
    "phone": "phone",
    "student": "student_full_name",
    "grade": "grade",
    "school": "current_school",
    "neighborhood": "neighborhood",
    "location": "olympiad_location",
    "source": "source",
}


class AdminStates(StatesGroup):
    search_query = State()
    delete_code = State()
    attended_code = State()
    broadcast_text = State()
    edit_command = State()
    answer_key = State()


def is_admin(message: Message, config: Config) -> bool:
    return bool(message.from_user and message.from_user.id in config.admin_ids)


async def require_admin(message: Message, config: Config) -> bool:
    if is_admin(message, config):
        return True
    await message.answer("Bu buyruq faqat administratorlar uchun.")
    return False


def code_arg(command: CommandObject) -> str:
    return clean_text(command.args or "", 40).upper()


@router.message(Command("myid"))
async def my_id(message: Message) -> None:
    if message.from_user:
        await message.answer(f"Sizning Telegram ID raqamingiz: {message.from_user.id}")


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Joriy jarayon bekor qilindi.")


@router.message(Command("help"))
async def help_command(message: Message, config: Config) -> None:
    text = (
        "Algoritm School Olimpiada bot buyruqlari:\n\n"
        "/start - ro'yxatdan o'tish yoki mavjud arizani ko'rish\n"
        "/myid - Telegram ID raqamingizni ko'rish\n"
        "/cancel - joriy jarayonni bekor qilish\n"
    )
    if is_admin(message, config):
        text += (
            "\nAdmin buyruqlari:\n"
            "/stats - umumiy statistika\n"
            "/export - CSV faylni olish\n"
            "/search <matn> - telefon, ism yoki kod bo'yicha qidirish\n"
            "/locations - hududlar statistikasi\n"
            "/grades - sinflar statistikasi\n"
            "/today - bugungi arizalar\n"
            "/recent - oxirgi 10 ta ariza\n"
            "/delete <AS-0001> - arizani o'chirish\n"
            "/attended <AS-0001> - keldi holatiga o'tkazish\n"
            "/edit <AS-0001> <maydon> <yangi qiymat> - arizani tahrirlash\n"
            "/broadcast <xabar> - barcha ro'yxatdan o'tganlarga xabar yuborish\n"
            "/setkeys <1A2B...30D> - sinov javob kalitlarini kiritish\n"
            "/answers - yuborilgan sinov javoblari natijalari\n"
            "/export_answers - sinov natijalarini CSV qilib olish\n\n"
            "Tahrirlash maydonlari: parent, phone, student, grade, school, "
            "neighborhood, location, source."
        )
    await message.answer(text)


@router.message(Command("stats"))
async def stats(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    data = await database.stats()
    by_source = format_counts(data["by_source"])
    await message.answer(
        "Umumiy statistika:\n\n"
        f"Jami ro'yxatdan o'tganlar: {data['total']}\n"
        f"2-sinflar: {data['by_grade'].get('2-sinf', 0)}\n"
        f"3-sinflar: {data['by_grade'].get('3-sinf', 0)}\n"
        f"4-sinflar: {data['by_grade'].get('4-sinf', 0)}\n"
        f"Bugungi arizalar: {data['today']}\n"
        f"Keldi: {data['attended']}\n"
        f"Kelmagan: {data['not_attended']}\n\n"
        f"Reklama manbalari:\n{by_source}"
    )


@router.message(Command("locations"))
async def locations(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    data = await database.stats()
    await message.answer("Hududlar bo'yicha statistika:\n\n" + format_counts(data["by_location"]))


@router.message(Command("grades"))
async def grades(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    data = await database.stats()
    await message.answer("Sinflar bo'yicha statistika:\n\n" + format_counts(data["by_grade"]))


@router.message(Command("today"))
async def today(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    rows = await database.today()
    await message.answer(format_rows(f"Bugungi arizalar: {len(rows)}", rows))


@router.message(Command("recent"))
async def recent(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    rows = await database.recent(10)
    await message.answer(format_rows("Oxirgi 10 ta ariza", rows))


@router.message(Command("export"))
async def export(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    data = await database.export_csv()
    with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as file:
        file.write(data)
        path = Path(file.name)
    try:
        await message.answer_document(
            FSInputFile(path, filename="algoritm_school_olimpiada.csv"),
            caption="CSV fayl UTF-8 BOM bilan tayyorlandi. Excel'da o'zbek harflari to'g'ri ochiladi.",
        )
    finally:
        path.unlink(missing_ok=True)


@router.message(Command("search"))
async def search_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if not await require_admin(message, config):
        return
    query = clean_text(command.args or "", 80)
    if not query:
        await state.set_state(AdminStates.search_query)
        await message.answer("Qidirish uchun telefon, ism yoki ishtirokchi kodini yuboring.")
        return
    await send_search_results(message, database, query)


@router.message(AdminStates.search_query, F.text)
async def search_state(message: Message, state: FSMContext, database: Database) -> None:
    await state.clear()
    await send_search_results(message, database, clean_text(message.text or "", 80))


@router.message(Command("delete"))
async def delete_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if not await require_admin(message, config):
        return
    code = code_arg(command)
    if not code:
        await state.set_state(AdminStates.delete_code)
        await message.answer("O'chirish uchun ishtirokchi kodini yuboring. Masalan: AS-0001")
        return
    await delete_by_code(message, database, code)


@router.message(AdminStates.delete_code, F.text)
async def delete_state(message: Message, state: FSMContext, database: Database) -> None:
    await state.clear()
    await delete_by_code(message, database, clean_text(message.text or "", 40).upper())


@router.message(Command("attended"))
async def attended_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if not await require_admin(message, config):
        return
    code = code_arg(command)
    if not code:
        await state.set_state(AdminStates.attended_code)
        await message.answer("Keldi holatiga o'tkazish uchun kodni yuboring. Masalan: AS-0001")
        return
    await mark_attended(message, database, code)


@router.message(AdminStates.attended_code, F.text)
async def attended_state(message: Message, state: FSMContext, database: Database) -> None:
    await state.clear()
    await mark_attended(message, database, clean_text(message.text or "", 40).upper())


@router.message(Command("edit"))
async def edit_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if not await require_admin(message, config):
        return
    args = clean_text(command.args or "", 260)
    if not args:
        await state.set_state(AdminStates.edit_command)
        await message.answer(
            "Tahrirlash formati: AS-0001 maydon yangi qiymat\n"
            "Masalan: AS-0001 grade 3-sinf"
        )
        return
    await edit_registration(message, database, args)


@router.message(AdminStates.edit_command, F.text)
async def edit_state(message: Message, state: FSMContext, database: Database) -> None:
    await state.clear()
    await edit_registration(message, database, clean_text(message.text or "", 260))


@router.message(Command("broadcast"))
async def broadcast_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if not await require_admin(message, config):
        return
    text = clean_text(command.args or "", 3500)
    if not text:
        await state.set_state(AdminStates.broadcast_text)
        await message.answer("Yuboriladigan xabar matnini kiriting.")
        return
    await send_broadcast(message, database, text)


@router.message(AdminStates.broadcast_text, F.text)
async def broadcast_state(message: Message, state: FSMContext, database: Database) -> None:
    await state.clear()
    await send_broadcast(message, database, clean_text(message.text or "", 3500))


@router.message(Command("setkeys"))
async def set_keys_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if not await require_admin(message, config):
        return
    raw_answers = clean_text(command.args or "", 220)
    if not raw_answers:
        await state.set_state(AdminStates.answer_key)
        await message.answer(
            "30 ta kalit javobni yuboring.\n\n"
            "Namuna:\n"
            "1A2B3C4D5A...30D"
        )
        return
    await set_answer_key(message, database, raw_answers)


@router.message(AdminStates.answer_key, F.text)
async def set_keys_state(message: Message, state: FSMContext, database: Database) -> None:
    await state.clear()
    await set_answer_key(message, database, clean_text(message.text or "", 220))


@router.message(Command("answers"))
async def answers_command(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    rows = await database.all_answer_submissions()
    await message.answer(format_answer_rows(rows))


@router.message(Command("export_answers"))
async def export_answers(message: Message, database: Database, config: Config) -> None:
    if not await require_admin(message, config):
        return
    data = await database.export_answer_submissions_csv()
    with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as file:
        file.write(data)
        path = Path(file.name)
    try:
        await message.answer_document(
            FSInputFile(path, filename="algoritm_school_sinov_natijalari.csv"),
            caption="Sinov javoblari va natijalari CSV faylga chiqarildi.",
        )
    finally:
        path.unlink(missing_ok=True)


async def send_search_results(message: Message, database: Database, query: str) -> None:
    rows = await database.search(query)
    if not rows:
        await message.answer("Hech narsa topilmadi.")
        return
    await message.answer(format_rows(f"Qidiruv natijalari: {len(rows)}", rows, detailed=True))


async def delete_by_code(message: Message, database: Database, code: str) -> None:
    deleted = await database.delete_by_code(code)
    await message.answer("Ariza o'chirildi." if deleted else "Bunday kod topilmadi.")


async def mark_attended(message: Message, database: Database, code: str) -> None:
    row = await database.mark_attended(code)
    if not row:
        await message.answer("Bunday kod topilmadi.")
        return
    await message.answer(f"Keldi holatiga o'tkazildi:\n\n{registration_summary(row)}")


async def edit_registration(message: Message, database: Database, args: str) -> None:
    parts = args.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Format noto'g'ri. Masalan: AS-0001 grade 3-sinf")
        return
    code, raw_field, value = parts
    field = EDIT_FIELDS.get(raw_field)
    if not field:
        await message.answer("Noto'g'ri maydon. /help orqali maydonlar ro'yxatini ko'ring.")
        return
    value = clean_text(value)
    validator = field_validator(field)
    if validator:
        try:
            value = validator(value)
        except ValueError as exc:
            await message.answer(str(exc))
            return
    row = await database.update_field(code.upper(), field, value)
    if not row:
        await message.answer("Bunday kod topilmadi.")
        return
    await message.answer("Ariza yangilandi:\n\n" + registration_summary(row))


async def send_broadcast(message: Message, database: Database, text: str) -> None:
    rows = await database.all_registrations()
    sent = 0
    failed = 0
    await message.answer(f"Broadcast boshlandi. Jami: {len(rows)}")
    for row in rows:
        try:
            await message.bot.send_message(int(row["telegram_id"]), text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(f"Broadcast yakunlandi.\nYuborildi: {sent}\nXatolik: {failed}")


async def set_answer_key(message: Message, database: Database, raw_answers: str) -> None:
    try:
        answers_text = parse_answer_text(raw_answers)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await database.set_answer_key(answers_text)
    submissions = await database.all_answer_submissions()
    for submission in submissions:
        correct_count, _ = score_answers(submission["answers_text"], answers_text)
        await database.update_answer_submission_score(submission["id"], correct_count)

    await message.answer(
        "Kalit javoblar saqlandi.\n\n"
        f"Savollar soni: {TEST_QUESTION_COUNT}\n"
        f"Qayta tekshirilgan javoblar: {len(submissions)}"
    )


def field_validator(field: str) -> Optional[Callable[[str], str]]:
    validators = {
        "phone": normalize_phone,
        "grade": validate_grade,
        "olympiad_location": validate_location,
    }
    return validators.get(field)


def validate_grade(value: str) -> str:
    if value not in GRADES:
        raise ValueError("Sinf faqat 2-sinf, 3-sinf yoki 4-sinf bo'lishi mumkin.")
    return value


def validate_location(value: str) -> str:
    if value not in OLYMPIAD_LOCATIONS:
        raise ValueError("Hudud tugmalardagi qiymatlardan biri bo'lishi kerak.")
    return value


def format_counts(counts: dict) -> str:
    if not counts:
        return "Ma'lumot yo'q."
    return "\n".join(f"{label}: {count}" for label, count in counts.items())


def format_rows(title: str, rows: list, detailed: bool = False) -> str:
    if not rows:
        return title + "\n\nMa'lumot yo'q."
    lines = [title, ""]
    for row in rows:
        if detailed:
            lines.append(registration_summary(row))
        else:
            lines.append(
                f"{row['participant_code']} | {row['student_full_name']} | "
                f"{row['grade']} | {row['olympiad_location']}"
            )
        lines.append("")
    return "\n".join(lines).strip()


def format_answer_rows(rows: list) -> str:
    if not rows:
        return "Hali sinov javoblari yuborilmagan."
    lines = [f"Sinov javoblari: {len(rows)}", ""]
    for row in rows[:30]:
        result = (
            "Kalit kutilmoqda"
            if row["correct_count"] is None
            else f"{row['correct_count']}/{row['total_questions']}"
        )
        lines.append(
            f"{row['participant_code']} | {row['student_full_name']} | "
            f"{row['grade']} | {result}"
        )
    if len(rows) > 30:
        lines.append("")
        lines.append("Yana natijalar bor. To'liq ro'yxat uchun /export_answers.")
    return "\n".join(lines)
