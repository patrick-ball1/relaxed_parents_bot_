"""
relaxed_parents_bot — прогревающая воронка «Академия Родителей»
Схема воронки (на основе схемы):

Старт → вебинар (сразу)
→ 10 мин (если не нажал) → напоминание о вебинаре
→ 1 час → 2-е напоминание о вебинаре
→ 12 часов → соц. доказательство (1000+ мам)
→ 30 мин → питч академии (верхушка айсберга)
→ 3 часа → оффер 4980Т
→ 6 часов → отзывы Telegram
→ 12 часов → история Юлии
→ 12 часов → финальный призыв
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeDefault,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, ACADEMY_URL, GUIDE_PDF_PATH, VIDEO_DAY1_PATH
from database import Database
from analytics import log_event
from excel_report import rebuild_excel, EXCEL_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

db = Database()
scheduler = AsyncIOScheduler()

# ── Ссылки (настройте в config.py или через ENV) ─────────────────────────────
WEBINAR_URL   = os.getenv("WEBINAR_URL",  "https://youtu.be/hmeUnKo_twc?si=zlzdR78cqM-gzN6b")
REVIEWS_URL   = os.getenv("REVIEWS_URL",  "https://t.me/+SNRZMUcm-9M5MzEy")
BOT_LINK      = os.getenv("BOT_LINK",     "https://t.me/relaxed_parents_bot")   # ссылка на самого бота (для кнопок «Вступить»)


# ──────────────────────────────────────────────
# FSM States
# ──────────────────────────────────────────────
class UserForm(StatesGroup):
    waiting_for_name = State()


# ──────────────────────────────────────────────
# Меню команд
# ──────────────────────────────────────────────
BOT_COMMANDS = [
    BotCommand(command="start", description="🚀 Начать"),
]


# ──────────────────────────────────────────────
# Keyboards
# ──────────────────────────────────────────────
def webinar_keyboard(label: str = "СМОТРЕТЬ УРОК 🎬"):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, url=WEBINAR_URL)]]
    )

def academy_join_keyboard(label: str = "ПОПРОБОВАТЬ 🎓"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label,          url=BOT_LINK)],
            [InlineKeyboardButton(text="ПОДРОБНЕЕ 📖", url=BOT_LINK)],
        ]
    )

def join_keyboard(label: str = "Вступаю в канал 🎓"):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, url=BOT_LINK)]]
    )

def reviews_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="👇 Смотри отзывы 👇", url=REVIEWS_URL)]]
    )


# ──────────────────────────────────────────────
# Helper: последовательная отправка сообщений
# ──────────────────────────────────────────────
async def send_sequence(chat_id: int, messages: list):
    for i, msg in enumerate(messages):
        if i > 0:
            await asyncio.sleep(msg.get("pause", 5))
        await bot.send_message(
            chat_id,
            msg["text"],
            reply_markup=msg.get("reply_markup"),
            parse_mode=msg.get("parse_mode"),
        )


# ──────────────────────────────────────────────
# Команды меню
# ──────────────────────────────────────────────
@router.message(Command("webinar"))
async def cmd_webinar(message: Message):
    await message.answer(
        "🎬 Бесплатный урок доктора Эламана — смотрите прямо сейчас:",
        reply_markup=webinar_keyboard("СМОТРЕТЬ УРОК 🎬"),
    )

@router.message(Command("academy"))
async def cmd_academy(message: Message):
    await message.answer(
        "🎓 *Академия Родителей* — ежедневная поддержка в первый год.\n\n"
        "• Советы по возрасту малыша\n"
        "• Ответы от экспертов\n"
        "• Планы развития по неделям\n\n"
        "Доступ всего за *4980₸ (~$9,5) в месяц* 🎁",
        parse_mode="Markdown",
        reply_markup=join_keyboard("Вступить в Академию 🎓"),
    )

@router.message(Command("reviews"))
async def cmd_reviews(message: Message):
    await message.answer(
        "💬 Что говорят мамы, которые уже с нами:",
        reply_markup=reviews_keyboard(),
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ *Помощь:*\n\n"
        "/webinar — бесплатный вебинар\n"
        "/academy — Академия Родителей\n"
        "/reviews — отзывы участников\n\n"
        "Или просто напишите свой вопрос — ассистент ответит 💙",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# Старт — День 0
# ──────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await db.ensure_user(user_id)
    await log_event(user_id, "bot_started")

    await message.answer(
        "Привет, ты в заботливом месте! 💛\n\n"
        "Здесь мамы малышей от 0 до 1 годика находят ответы "
        "на ежедневные «как?», «что если?», «нормально ли это?»\n\n"
        "Получишь бесплатный мини-вебинар с ответами на самые частые вопросы, "
        "которые мешают спать спокойно 👇",
        reply_markup=webinar_keyboard("СМОТРЕТЬ УРОК 🎬"),
    )
    await log_event(user_id, "webinar_offered")

    # Запускаем всю цепочку напоминаний
    await db.set_start_time(user_id, datetime.utcnow())
    await schedule_funnel(user_id)


# ──────────────────────────────────────────────
# Воронка: сообщения по таймеру
# ──────────────────────────────────────────────

# ── Напоминание 1: через 10 минут ─────────────
async def remind_webinar_10min(user_id: int):
    await bot.send_message(
        user_id,
        "Ты не успела посмотреть вебинар? Это нормально — мама с малышом живёт по особому расписанию 🌙\n\n"
        "Но эти 20 минут могут избавить тебя от часов гугления и тревог.\n\n"
        "Смотри в удобное время — вебинар ждёт тебя здесь 👇",
        reply_markup=webinar_keyboard("СМОТРЕТЬ ВЕБИНАР 🎬"),
    )
    await log_event(user_id, "remind_10min_sent")


# ── Напоминание 2: через 1 час ─────────────────
async def remind_webinar_1h(user_id: int):
    await bot.send_message(
        user_id,
        "Каждый день в Академии — это новый ответ, новая уверенность.\n\n"
        "А пока ты ещё не с нами — вопросы продолжают накапливаться.\n\n"
        "Пока вебинар доступен — успей посмотреть и узнать, как мы можем тебе помочь 💕",
        reply_markup=webinar_keyboard("Смотреть вебинар 🎬"),
    )
    await log_event(user_id, "remind_1h_sent")


# ── Через 12 часов: соц. доказательство ────────
async def social_proof_12h(user_id: int):
    await bot.send_message(
        user_id,
        "Более 1000 мам уже посмотрели вебинар и присоединились к Академии.\n\n"
        "И почти каждая говорила одно: **«Жаль, что не раньше...»**\n\n"
        "Сделай это для себя. Для малыша.\n\n"
        "Потрать 20 минут — и получи спокойствие на месяцы вперёд 👇",
        parse_mode="Markdown",
        reply_markup=webinar_keyboard("СМОТРЕТЬ ВЕБИНАР 🎬"),
    )
    await log_event(user_id, "social_proof_12h_sent")


# ── Через 30 мин после 12ч: питч академии ───────
async def pitch_academy(user_id: int):
    name = await db.get_user_name(user_id)
    await send_sequence(user_id, [
        {
            "text": "Наш вебинар — только верхушка айсберга!\n\n"
                    "Представь, что каждый день ты получаешь:\n\n"
                    "✨ Советы по возрасту малыша\n"
                    "✨ Ответы от экспертов\n"
                    "✨ Планы развития по неделям\n\n"
                    "Это всё ждёт тебя в Академии Родителей!",
            "reply_markup": academy_join_keyboard(),
            "pause": 0,
        },
    ])
    await log_event(user_id, "pitch_academy_sent")


# ── Через 3 часа: оффер 4980Т ──────────────────
async def offer_3h(user_id: int):
    await bot.send_message(
        user_id,
        "Каждый день — новые вопросы...\n\n"
        "Но тебе не нужно больше искать ответы в Instagram и на форумах 📱💻\n\n"
        "Пусть Академия Родителей станет твоей опорой, уверенной поддержкой и источником спокойствия 🌿\n\n"
        "Присоединяйся к сотням мам, которые уже с нами!\n\n"
        "Хочешь получить доступ на целый месяц всего за 4980₸ (~ $9,5)? 🎁\n"
        "Вступаю в канал (ссылка на бот)",
        reply_markup=join_keyboard("Вступаю в канал 🎓"),
    )
    await log_event(user_id, "offer_3h_sent")


# ── Через 6 часов: отзывы ──────────────────────
async def reviews_6h(user_id: int):
    await bot.send_message(
        user_id,
        "Хочешь узнать, что говорят другие мамы, которые уже с нами? 💬\n\n"
        "Они были на твоём месте — растерянные, уставшие, с сотнями вопросов. А теперь... читай сама:",
        reply_markup=reviews_keyboard(),
    )
    await log_event(user_id, "reviews_6h_sent")


# ── Через 12 часов: история Юлии ───────────────
async def story_julia_12h(user_id: int):
    await bot.send_message(
        user_id,
        "Спокойная мама — это всегда счастливый малыш🧡\n\n"
        "Юлия — одна из наших подписчиц, тоже отмечает, что канал значительно облегчил её путь в материнстве, "
        "ведь здесь всегда рядом специалисты, готовые поддержать и помочь 🤝\n\n"
        "В нашем канале есть все специалисты, которые необходимы для помощи всем родителям по проблемам "
        "хаотичного сна, частых пробуждений, ГВ, ИВ, коликам и прочим горячим вопросам.\n\n"
        "Вступить - ссылка на бот",
        reply_markup=join_keyboard("Вступить 💙"),
    )
    await log_event(user_id, "story_julia_sent")


# ── Через 12 часов: финал ──────────────────────
async def final_message(user_id: int):
    await bot.send_message(
        user_id,
        "Ждем, чтобы ты стал более расслабленным родителем ❤️❤️❤️\n\n"
        "Присоединиться! (ссылка на бот)",
        reply_markup=join_keyboard("Присоединиться! 🎓"),
    )
    await log_event(user_id, "final_message_sent")
    await db.set_user_stage(user_id, "general_base")


# ──────────────────────────────────────────────
# Планировщик воронки
# ──────────────────────────────────────────────
async def schedule_funnel(user_id: int):
    start = await db.get_start_time(user_id)

    # (минуты_от_старта, job_id, функция)
    schedule = [
        (10,    "remind_10min",    remind_webinar_10min),
        (60,    "remind_1h",       remind_webinar_1h),
        (720,   "social_proof",    social_proof_12h),
        (750,   "pitch_academy",   pitch_academy),      # +30 мин после 12ч
        (930,   "offer_3h",        offer_3h),           # +3ч после питча
        (1290,  "reviews_6h",      reviews_6h),         # +6ч после оффера
        (2010,  "story_julia",     story_julia_12h),    # +12ч после отзывов
        (2730,  "final_msg",       final_message),      # +12ч после истории
    ]

    for minutes, job_id, func in schedule:
        run_at = start + timedelta(minutes=minutes)
        jid = f"{user_id}_{job_id}"
        if not scheduler.get_job(jid):
            scheduler.add_job(
                func, "date",
                run_date=run_at,
                args=[user_id],
                id=jid,
                replace_existing=True,
            )
            logger.info(f"Scheduled {jid} at {run_at}")


# ──────────────────────────────────────────────
# Ключевые слова → автоответы
# ──────────────────────────────────────────────
KEYWORD_RESPONSES = {
    ("вебинар", "урок", "видео", "ютуб", "youtube"): (
        "🎬 Бесплатный вебинар доктора Эламана ждёт тебя:\n\n"
        f"{WEBINAR_URL}\n\nИли нажми /webinar"
    ),
    ("академия", "курс", "подписка", "купить", "цена", "стоимость", "доступ", "вступить"): (
        "🎓 *Академия Родителей* — всё необходимое в первый год.\n\n"
        "Доступ всего за 4980₸ (~$9,5) в месяц!\n\n"
        "Подробнее → /academy"
    ),
    ("отзывы", "отзыв", "мнение", "говорят мамы"): (
        "💬 Отзывы участников читайте здесь → /reviews"
    ),
    ("температура", "жар", "горит"): (
        "🌡 При температуре у малыша:\n\n"
        "• До 3 мес — t° выше 38°C → скорая (103)\n"
        "• После 3 мес — сбивать при t° выше 38.5°C\n\n"
        "✅ Парацетамол или Ибупрофен (с 3 мес)\n"
        "❌ Аспирин — никогда!"
    ),
    ("колики", "живот", "газы", "плачет", "кричит"): (
        "👶 Колики — норма до 3–4 мес.\n\n"
        "✅ Тепло на животик, «велосипед», выкладывание\n"
        "❌ Эспумизан, Плантекс — не эффективнее плацебо"
    ),
    ("сон", "не спит", "ночью", "засыпает"): (
        "😴 Нормы сна:\n"
        "0–3 мес — 14–17ч | 3–6 мес — 12–15ч | 6–12 мес — 11–14ч\n\n"
        "Частые пробуждения до 6 мес — норма!"
    ),
    ("насморк", "нос", "сопли", "заложен"): (
        "👃 При насморке:\n\n"
        "✅ Физраствор NaCl 0.9%, увлажнять воздух\n"
        "❌ Сосудосуживающие до года — только по назначению врача"
    ),
}

def find_keyword_response(text: str):
    text_lower = text.lower()
    for keywords, response in KEYWORD_RESPONSES.items():
        for kw in keywords:
            if kw in text_lower:
                return response
    return None


# ──────────────────────────────────────────────
# Catch-all: свободный текст
# ──────────────────────────────────────────────
@router.message()
async def handle_free_text(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == UserForm.waiting_for_name:
        return

    text = message.text or ""
    response = find_keyword_response(text)

    if response:
        await message.answer(response, parse_mode="Markdown")
    else:
        await message.answer(
            "Спасибо за сообщение! Ассистент получил его и скоро ответит. 💙\n\n"
            "Или воспользуйтесь командами — нажмите / чтобы увидеть список.",
        )


# ──────────────────────────────────────────────
# Запуск
# ──────────────────────────────────────────────
async def main():
    await db.init()

    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
    logger.info("Bot commands menu set")

    await rebuild_excel()
    logger.info(f"Excel analytics ready: {EXCEL_PATH}")

    scheduler.add_job(
        rebuild_excel, "cron", hour=6, minute=0,
        id="daily_excel_rebuild", replace_existing=True,
    )

    scheduler.start()
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
