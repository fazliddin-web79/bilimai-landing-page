from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config import Config
from bot.constants import GRADES, OLYMPIAD_LOCATIONS, TEST_QUESTION_COUNT, UNKNOWN_SOURCE
from bot.database import Database, DuplicateTelegramError
from bot.keyboards import (
    confirmation_keyboard,
    contact_keyboard,
    grades_keyboard,
    locations_keyboard,
    registered_user_keyboard,
    registration_keyboard,
    remove_keyboard,
)
from bot.registration import build_registration_input
from bot.utils import (
    clean_text,
    confirmation_text,
    normalize_phone,
    olympiad_schedule_text,
    parse_answer_text,
    score_answers,
)

router = Router()


class RegistrationStates(StatesGroup):
    parent_full_name = State()
    phone = State()
    student_full_name = State()
    grade = State()
    current_school = State()
    neighborhood = State()
    olympiad_location = State()
    confirmation = State()
    test_answers = State()


WELCOME_TEXT = (
    "Assalomu alaykum!\n\n"
    "Algoritm School Olimpiada botiga xush kelibsiz. Bu bot 2-, 3- va "
    "4-sinf o'quvchilarini Prezident maktabiga tayyorgarlik olimpiadasiga "
    "ro'yxatdan o'tkazadi.\n\n"
    "Jarayon bir necha daqiqa davom etadi. Boshlash uchun tugmani bosing."
)


@router.message(CommandStart())
async def start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    database: Database,
) -> None:
    if message.from_user is None:
        return
    await state.clear()
    existing = await database.get_by_telegram_id(message.from_user.id)
    if existing:
        await message.answer(
            "Siz avval ro'yxatdan o'tgansiz.\n\n"
            f"O'quvchi: {existing['student_full_name']}\n"
            f"Sinf: {existing['grade']}\n"
            f"Olimpiada manzili: {existing['olympiad_location']}"
            f"{olympiad_schedule_text(existing['olympiad_location'])}\n"
            f"Ishtirokchi kodi: {existing['participant_code']}\n\n"
            "Iltimos, ushbu kodni saqlab qo'ying.\n\n"
            "Sinov javoblarini yuborish uchun pastdagi tugmani bosing.",
            reply_markup=registered_user_keyboard(),
        )
        return

    source = clean_text(command.args or UNKNOWN_SOURCE, 60) or UNKNOWN_SOURCE
    await state.update_data(source=source)
    await message.answer(WELCOME_TEXT, reply_markup=registration_keyboard())


@router.message(F.text == "Sinov javoblarini jo'natish")
async def begin_test_answers(
    message: Message,
    state: FSMContext,
    database: Database,
) -> None:
    if message.from_user is None:
        return
    registration = await database.get_by_telegram_id(message.from_user.id)
    if not registration:
        await message.answer(
            "Avval olimpiadaga ro'yxatdan o'ting. /start buyrug'ini bosing.",
            reply_markup=registration_keyboard(),
        )
        return
    await state.set_state(RegistrationStates.test_answers)
    await message.answer(
        "30 ta savol javobini bitta xabar qilib yuboring.\n\n"
        "Format:\n"
        "1A2B3C4D5A...30D\n\n"
        "Faqat A, B, C, D variantlari qabul qilinadi.",
        reply_markup=remove_keyboard(),
    )


@router.message(F.text == "Ro'yxatdan o'tish")
async def begin_registration(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.parent_full_name)
    await message.answer(
        "Ota-ona yoki mas'ul shaxsning ism-familiyasini yozing:",
        reply_markup=remove_keyboard(),
    )


@router.message(RegistrationStates.parent_full_name, F.text)
async def parent_full_name(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "")
    if len(value) < 3:
        await message.answer("Iltimos, ism-familiyani to'liqroq kiriting.")
        return
    await state.update_data(parent_full_name=value)
    await state.set_state(RegistrationStates.phone)
    await message.answer(
        "Telefon raqamingizni maxsus tugma orqali ulashing yoki matn ko'rinishida yuboring:",
        reply_markup=contact_keyboard(),
    )


@router.message(RegistrationStates.phone)
async def phone(message: Message, state: FSMContext) -> None:
    raw_phone = message.contact.phone_number if message.contact else message.text
    if not raw_phone:
        await message.answer("Telefon raqamni yuboring.")
        return
    try:
        normalized = normalize_phone(raw_phone)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(phone=normalized)
    await state.set_state(RegistrationStates.student_full_name)
    await message.answer(
        "O'quvchining ism-familiyasini yozing:",
        reply_markup=remove_keyboard(),
    )


@router.message(RegistrationStates.student_full_name, F.text)
async def student_full_name(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "")
    if len(value) < 3:
        await message.answer("Iltimos, o'quvchi ism-familiyasini to'liqroq kiriting.")
        return
    await state.update_data(student_full_name=value)
    await state.set_state(RegistrationStates.grade)
    await message.answer("O'quvchining sinfini tanlang:", reply_markup=grades_keyboard())


@router.message(RegistrationStates.grade, F.text)
async def grade(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "")
    if value not in GRADES:
        await message.answer("Iltimos, sinfni tugmalar orqali tanlang.", reply_markup=grades_keyboard())
        return
    await state.update_data(grade=value)
    await state.set_state(RegistrationStates.current_school)
    await message.answer(
        "O'quvchi hozir o'qiydigan maktab raqami yoki nomini yozing:",
        reply_markup=remove_keyboard(),
    )


@router.message(RegistrationStates.current_school, F.text)
async def current_school(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "")
    if len(value) < 1:
        await message.answer("Maktab raqami yoki nomini kiriting.")
        return
    await state.update_data(current_school=value)
    await state.set_state(RegistrationStates.neighborhood)
    await message.answer("Yashash hududi yoki mahallangizni yozing:")


@router.message(RegistrationStates.neighborhood, F.text)
async def neighborhood(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "")
    if len(value) < 2:
        await message.answer("Hudud yoki mahalla nomini to'liqroq kiriting.")
        return
    await state.update_data(neighborhood=value)
    await state.set_state(RegistrationStates.olympiad_location)
    await message.answer(
        "Olimpiadaga borish uchun eng qulay hududni tanlang:",
        reply_markup=locations_keyboard(),
    )


@router.message(RegistrationStates.olympiad_location, F.text)
async def olympiad_location(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "")
    if value not in OLYMPIAD_LOCATIONS:
        await message.answer(
            "Iltimos, olimpiada hududini tugmalar orqali tanlang.",
            reply_markup=locations_keyboard(),
        )
        return
    await state.update_data(olympiad_location=value)
    data = await state.get_data()
    await state.set_state(RegistrationStates.confirmation)
    await message.answer(
        confirmation_text(data),
        reply_markup=confirmation_keyboard(),
    )


@router.message(RegistrationStates.confirmation, F.text == "Qayta boshlash")
async def restart_registration(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await state.update_data(source=data.get("source", UNKNOWN_SOURCE))
    await begin_registration(message, state)


@router.message(RegistrationStates.confirmation, F.text == "Tasdiqlayman")
async def confirm_registration(
    message: Message,
    state: FSMContext,
    database: Database,
    config: Config,
) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    username = message.from_user.username
    registration = build_registration_input(message.from_user.id, username, data)
    try:
        same_phone_count = await database.phone_count(registration.phone, registration.telegram_id)
        saved = await database.create_registration(registration)
    except DuplicateTelegramError:
        saved = await database.get_by_telegram_id(message.from_user.id)
        if saved:
            await message.answer(
                "Siz avval ro'yxatdan o'tgansiz.\n\n"
                f"Ishtirokchi kodi: {saved['participant_code']}",
                reply_markup=remove_keyboard(),
            )
        await state.clear()
        return

    await state.clear()
    await message.answer(
        "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!\n\n"
        f"O'quvchi: {saved['student_full_name']}\n"
        f"Sinf: {saved['grade']}\n"
        f"Olimpiada manzili: {saved['olympiad_location']}"
        f"{olympiad_schedule_text(saved['olympiad_location'])}\n"
        f"Ishtirokchi kodi: {saved['participant_code']}\n\n"
        "Iltimos, ishtirokchi kodingizni saqlab qo'ying.",
        reply_markup=remove_keyboard(),
    )

    if same_phone_count > 0:
        for admin_id in config.admin_ids:
            await message.bot.send_message(
                admin_id,
                "Ogohlantirish: takroriy telefon raqam bilan yangi ariza keldi.\n\n"
                f"Yangi kod: {saved['participant_code']}\n"
                f"O'quvchi: {saved['student_full_name']}\n"
                f"Telefon: {saved['phone']}",
            )


@router.message(RegistrationStates.confirmation)
async def wrong_confirmation(message: Message) -> None:
    await message.answer(
        "Iltimos, 'Tasdiqlayman' yoki 'Qayta boshlash' tugmasini tanlang.",
        reply_markup=confirmation_keyboard(),
    )


@router.message(RegistrationStates.test_answers, F.text)
async def save_test_answers(
    message: Message,
    state: FSMContext,
    database: Database,
) -> None:
    if message.from_user is None or message.text is None:
        return
    registration = await database.get_by_telegram_id(message.from_user.id)
    if not registration:
        await state.clear()
        await message.answer(
            "Avval olimpiadaga ro'yxatdan o'ting. /start buyrug'ini bosing.",
            reply_markup=registration_keyboard(),
        )
        return
    try:
        answers_text = parse_answer_text(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    answer_key = await database.get_answer_key()
    correct_count = None
    wrong_questions_text = ""
    if answer_key:
        correct_count, wrong_questions = score_answers(
            answers_text, answer_key["answers_text"]
        )
        if wrong_questions:
            wrong_questions_text = "\nXato savollar: " + ", ".join(
                str(number) for number in wrong_questions
            )

    submission = await database.save_answer_submission(
        registration,
        answers_text,
        correct_count,
        TEST_QUESTION_COUNT,
    )
    await state.clear()

    if correct_count is None:
        await message.answer(
            "Javoblaringiz qabul qilindi.\n\n"
            f"Ishtirokchi kodi: {submission['participant_code']}\n"
            "Admin kalit javoblarni kiritgandan keyin natija hisoblanadi.",
            reply_markup=registered_user_keyboard(),
        )
        return

    await message.answer(
        "Javoblaringiz qabul qilindi va tekshirildi.\n\n"
        f"Ishtirokchi kodi: {submission['participant_code']}\n"
        f"Natija: {correct_count}/{TEST_QUESTION_COUNT}"
        f"{wrong_questions_text}",
        reply_markup=registered_user_keyboard(),
    )
