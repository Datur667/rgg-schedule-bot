#!/usr/bin/env python3
"""
Telegram бот: Расписание РГГУ
Две чередующиеся недели, кнопки: сегодня / сейчас / неделя / след. неделя
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Московское время
MSK = ZoneInfo("Europe/Moscow")

# Ежедневные уведомления (по Москве)
NOTIFY_TIMES = [
    time(7, 30, tzinfo=MSK),   # 07:30
    time(20, 0, tzinfo=MSK),   # 20:00
]

# ==================== НАСТРОЙКИ ====================
import os
from aiogram import Bot
from aiogram.enums import ParseMode

# Получаем токен из переменной среды
token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    raise RuntimeError("Переменная TELEGRAM_BOT_TOKEN не задана!")

bot = Bot(token=token)

async def main():
    me = await bot.get_me()
    print(f"Бот запущен: @{me.username}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


# ==================== РАСПИСАНИЕ ====================
# Неделя 1
WEEK_1: Dict[str, List[Dict[str, str]]] = {
    "пн": [
        {"time": "9:00 - 10:00", "subject": "разговоры о важном"},
        {"time": "10:15 - 11:45", "subject": "история"},
        {"time": "11:55 - 13:25", "subject": "математика"},
        {"time": "13:50 - 15:20", "subject": "русский язык"},
    ],
    "вт": [
        {"time": "10:15 - 11:45", "subject": "математика"},
        {"time": "11:55 - 13:25", "subject": "биология"},
        {"time": "13:50 - 15:20", "subject": "история"},
        {"time": "15:35 - 17:05", "subject": "физика"},
    ],
    "ср": [
        {"time": "10:15 - 11:45", "subject": "информатика"},
        {"time": "11:55 - 13:25", "subject": "информатика"},
        {"time": "13:50 - 15:20", "subject": "литература"},
        {"time": "15:35 - 17:05", "subject": "английский язык"},
    ],
    "чт": [
        {"time": "11:55 - 13:25", "subject": "обществознание"},
        {"time": "13:50 - 15:20", "subject": "обществознание"},
    ],
    "пт": [
        {"time": "8:30 - 10:00", "subject": "химия"},
        {"time": "10:15 - 11:45", "subject": "география"},
        {"time": "11:55 - 13:25", "subject": "обж"},
        {"time": "15:00 - 16:30", "subject": "физра"},
    ],
}

# Неделя 2
WEEK_2: Dict[str, List[Dict[str, str]]] = {
    "пн": [
        {"time": "9:00 - 10:00", "subject": "разговоры о важном"},
        {"time": "10:15 - 11:45", "subject": "литература"},
        {"time": "11:55 - 13:25", "subject": "общество"},
        {"time": "13:50 - 15:20", "subject": "литература"},
        {"time": "15:35 - 17:05", "subject": "математика"},
    ],
    "вт": [
        {"time": "8:30 - 10:00", "subject": "русский язык"},
        {"time": "10:15 - 11:45", "subject": "математика"},
        {"time": "11:55 - 13:25", "subject": "информатика"},
    ],
    "ср": [
        {"time": "10:15 - 11:45", "subject": "английский язык"},
        {"time": "11:55 - 13:25", "subject": "английский язык"},
        {"time": "13:50 - 15:20", "subject": "математика"},
        {"time": "15:35 - 17:05", "subject": "история"},
    ],
    "чт": [
        {"time": "8:30 - 10:00", "subject": "химия"},
        {"time": "10:15 - 11:45", "subject": "физика"},
        {"time": "11:55 - 13:25", "subject": "индивидуальный проект"},
        {"time": "15:00 - 16:30", "subject": "физра"},
    ],
    "пт": [
        {"time": "10:15 - 11:45", "subject": "биология"},
        {"time": "11:55 - 13:25", "subject": "обж"},
        {"time": "13:50 - 15:20", "subject": "география"},
    ],
}

SCHEDULES = {1: WEEK_1, 2: WEEK_2}

DAY_NAMES = {
    0: "пн",
    1: "вт",
    2: "ср",
    3: "чт",
    4: "пт",
    5: "сб",
    6: "вс",
}

DAY_FULL = {
    "пн": "понедельник",
    "вт": "вторник",
    "ср": "среда",
    "чт": "четверг",
    "пт": "пятница",
    "сб": "суббота",
    "вс": "воскресенье",
}

DAY_EMOJI = {
    "пн": "1️⃣",
    "вт": "2️⃣",
    "ср": "3️⃣",
    "чт": "4️⃣",
    "пт": "5️⃣",
    "сб": "💤",
    "вс": "💤",
}


# ==================== ЛОГИКА ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_week_number(dt: Optional[datetime] = None) -> int:
    """Определяет номер недели (1 или 2) по ISO-неделе года.
    Сейчас (окт 2026) идёт 1-я неделя → чётная ISO-неделя = 1.
    """
    if dt is None:
        dt = datetime.now()
    iso_week = dt.isocalendar()[1]
    return 1 if iso_week % 2 == 0 else 2


def get_day_key(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = datetime.now()
    return DAY_NAMES[dt.weekday()]


def format_schedule(day_key: str, week: int, date_str: str = "", label: str = "") -> str:
    """Красивое оформление расписания на день."""
    schedule = SCHEDULES.get(week, {}).get(day_key, [])
    full_day = DAY_FULL.get(day_key, day_key).capitalize()
    emoji = DAY_EMOJI.get(day_key, "📌")

    # Заголовок
    header = f"{emoji} <b>{full_day}</b>"
    if date_str:
        header += f"  ·  <code>{date_str}</code>"
    if label:
        header += f"  ·  {label}"

    if not schedule:
        return f"{header}\n\n🎉  Выходной — пар нет\n\nМожно выдохнуть"

    lines = [header, ""]
    for i, pair in enumerate(schedule, 1):
        lines.append(f"<b>{i}.</b>  <code>{pair['time']}</code>")
        lines.append(f"      {pair['subject']}")
        if i < len(schedule):
            lines.append("────────────────")

    return "\n".join(lines)


def get_current_pair(week: int, day_key: str) -> Optional[Dict]:
    """Возвращает текущую пару или None."""
    now = datetime.now().time()
    schedule = SCHEDULES.get(week, {}).get(day_key, [])
    if not schedule:
        return None

    for pair in schedule:
        try:
            start_str, end_str = pair["time"].split(" - ")
            h1, m1 = map(int, start_str.split(":"))
            h2, m2 = map(int, end_str.split(":"))
            start_t = time(h1, m1)
            end_t = time(h2, m2)
            if start_t <= now <= end_t:
                return pair
        except Exception:
            continue
    return None


def main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню."""
    buttons = [
        [
            InlineKeyboardButton("📅  Сегодня", callback_data="cmd_today"),
            InlineKeyboardButton("⏰  Сейчас", callback_data="cmd_now"),
        ],
        [
            InlineKeyboardButton("🗓  Неделя", callback_data="cmd_week"),
            InlineKeyboardButton("➡️  След. неделя", callback_data="cmd_next_week"),
        ],
        [
            InlineKeyboardButton("①  1 неделя", callback_data="week_1"),
            InlineKeyboardButton("②  2 неделя", callback_data="week_2"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def week_days_keyboard(week: int) -> InlineKeyboardMarkup:
    """Кнопки дней + переключение недель."""
    buttons = [
        [
            InlineKeyboardButton("Пн", callback_data=f"day_{week}_пн"),
            InlineKeyboardButton("Вт", callback_data=f"day_{week}_вт"),
            InlineKeyboardButton("Ср", callback_data=f"day_{week}_ср"),
            InlineKeyboardButton("Чт", callback_data=f"day_{week}_чт"),
            InlineKeyboardButton("Пт", callback_data=f"day_{week}_пт"),
        ],
        [
            InlineKeyboardButton("①  1 нед.", callback_data="week_1"),
            InlineKeyboardButton("②  2 нед.", callback_data="week_2"),
        ],
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="cmd_today"),
            InlineKeyboardButton("⏰ Сейчас", callback_data="cmd_now"),
            InlineKeyboardButton("🏠 Меню", callback_data="menu"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ==================== ХЕНДЛЕРЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Сохраняем chat_id для ежедневных уведомлений
    chat_id = update.effective_chat.id
    context.application.bot_data.setdefault("subscribers", set()).add(chat_id)

    week = get_week_number()
    week_emoji = "①" if week == 1 else "②"
    text = (
        "╭─────────────────╮\n"
        "│  📚  <b>Расписание РГГУ</b>  │\n"
        "╰─────────────────╯\n\n"
        f"<i>? это очень необычно зайка</i>\n\n"
        f"бебебе\n\n"
        f"Сейчас идёт  <b>{week_emoji} неделя</b>\n"
        "Выбери, что нужно ↓"
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


async def send_today(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    now = datetime.now()
    week = get_week_number(now)
    day_key = get_day_key(now)
    date_str = now.strftime("%d.%m")
    text = format_schedule(day_key, week, date_str, "сегодня")
    text += f"\n\n────────────────\n🕐  {now.strftime('%H:%M')}   ·   неделя {week}"

    if is_callback:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())


async def send_now(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    now = datetime.now()
    week = get_week_number(now)
    day_key = get_day_key(now)
    pair = get_current_pair(week, day_key)
    day_name = DAY_FULL.get(day_key, day_key).capitalize()
    emoji = DAY_EMOJI.get(day_key, "📌")

    if pair:
        text = (
            f"⏰  <b>Сейчас идёт пара</b>\n\n"
            f"┌  <code>{pair['time']}</code>\n"
            f"└  <b>{pair['subject']}</b>\n\n"
            f"────────────────\n"
            f"{emoji}  {day_name}   ·   неделя {week}   ·   {now.strftime('%H:%M')}"
        )
    else:
        text = (
            f"☕  <b>Сейчас пары нет</b>\n\n"
            f"Можно выдохнуть и отдохнуть\n\n"
            f"────────────────\n"
            f"{emoji}  {day_name}   ·   неделя {week}   ·   {now.strftime('%H:%M')}"
        )

    if is_callback:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())


async def send_week(update: Update, context: ContextTypes.DEFAULT_TYPE, week: int = None, is_callback: bool = False) -> None:
    if week is None:
        week = get_week_number()
    emoji = "①" if week == 1 else "②"
    text = (
        f"{emoji}  <b>Неделя {week}</b>\n\n"
        f"Выбери день ↓"
    )
    markup = week_days_keyboard(week)

    if is_callback:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        week = get_week_number()
        week_emoji = "①" if week == 1 else "②"
        await query.edit_message_text(
            "╭─────────────────╮\n"
            "│  📚  <b>Расписание РГГУ</b>  │\n"
            "╰─────────────────╯\n\n"
            f"<i>? это очень необычно зайка</i>\n\n"
            f"бебебе\n\n"
            f"Сейчас идёт  <b>{week_emoji} неделя</b>\n"
            "Выбери, что нужно ↓",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    if data == "cmd_today":
        await send_today(update, context, is_callback=True)
        return

    if data == "cmd_now":
        await send_now(update, context, is_callback=True)
        return

    if data == "cmd_week":
        await send_week(update, context, is_callback=True)
        return

    if data == "cmd_next_week":
        next_week = 2 if get_week_number() == 1 else 1
        await send_week(update, context, week=next_week, is_callback=True)
        return

    if data.startswith("week_"):
        week = int(data.split("_")[1])
        await send_week(update, context, week=week, is_callback=True)
        return

    if data.startswith("day_"):
        parts = data.split("_")
        week = int(parts[1])
        day_key = parts[2]
        text = format_schedule(day_key, week, label=f"неделя {week}")
        text += f"\n\n────────────────\nнеделя {week}"
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=week_days_keyboard(week),
        )
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").lower().strip()

    if text in ("сегодня", "today"):
        await send_today(update, context)
    elif text in ("сейчас", "now"):
        await send_now(update, context)
    elif text == "неделя":
        await send_week(update, context)
    elif text in ("след. неделя", "следующая неделя", "след неделя"):
        next_week = 2 if get_week_number() == 1 else 1
        await send_week(update, context, week=next_week)
    elif text in ("1 неделя", "1неделя"):
        await send_week(update, context, week=1)
    elif text in ("2 неделя", "2неделя"):
        await send_week(update, context, week=2)
    else:
        await update.message.reply_text(
            "👇  Используй кнопки",
            reply_markup=main_keyboard(),
        )


async def daily_schedule_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Каждый день отправляет расписание на сегодня всем подписчикам (07:30 и 20:00 МСК)."""
    subscribers = context.application.bot_data.get("subscribers", set())
    if not subscribers:
        return

    now = datetime.now(MSK)
    week = get_week_number(now)
    day_key = get_day_key(now)
    date_str = now.strftime("%d.%m")

    text = format_schedule(day_key, week, date_str, "сегодня")
    text += f"\n\n────────────────\n🔔  Ежедневное напоминание  ·  неделя {week}  ·  {now.strftime('%H:%M')} МСК"

    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить {chat_id}: {e}")


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Ежедневные уведомления: 07:30 и 20:00 по Москве
    if app.job_queue:
        for i, t in enumerate(NOTIFY_TIMES):
            app.job_queue.run_daily(
                daily_schedule_job,
                time=t,
                name=f"daily_schedule_{i}",
            )
        print("Ежедневные уведомления: 07:30 и 20:00 (МСК)")
    else:
        print("JobQueue недоступен — ежедневные уведомления отключены")

    print("Бот запущен... (Ctrl+C для остановки)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

