#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram-бот: Расписание РГГУ
Две чередующиеся недели.
Кнопки: Сегодня / Сейчас / Неделя / Следующая неделя.
Уведомления: ежедневно в 07:30 и 20:00 по Москве.
"""

import os
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
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

# ==================================================
# НАСТРОЙКИ
# ==================================================

MSK = ZoneInfo("Europe/Moscow")

# Токен задаётся через переменную окружения BOT_TOKEN.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

NOTIFY_TIMES = [
    time(7, 30, tzinfo=MSK),
    time(20, 0, tzinfo=MSK),
]

# ==================================================
# РАСПИСАНИЕ — НЕДЕЛЯ 1
# ==================================================

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

# ==================================================
# РАСПИСАНИЕ — НЕДЕЛЯ 2
# ==================================================

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

SCHEDULES = {
    1: WEEK_1,
    2: WEEK_2,
}

# ==================================================
# ДНИ НЕДЕЛИ
# ==================================================

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

# ==================================================
# ЛОГИРОВАНИЕ
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ==================================================
# ОПРЕДЕЛЕНИЕ ДАТЫ И ВРЕМЕНИ
# ==================================================


def moscow_now() -> datetime:
    """Текущее московское время."""
    return datetime.now(MSK)


def get_week_number(dt: Optional[datetime] = None) -> int:
    """
    Определяет номер учебной недели.

    Правило из исходного кода:
    чётная ISO-неделя = неделя 1;
    нечётная ISO-неделя = неделя 2.

    Если у тебя есть точная дата начала первой учебной недели,
    это правило можно заменить привязкой к этой дате.
    """
    if dt is None:
        dt = moscow_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    else:
        dt = dt.astimezone(MSK)

    iso_week = dt.isocalendar().week

    return 1 if iso_week % 2 == 0 else 2


def get_day_key(dt: Optional[datetime] = None) -> str:
    """Возвращает короткое название дня недели."""
    if dt is None:
        dt = moscow_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    else:
        dt = dt.astimezone(MSK)

    return DAY_NAMES[dt.weekday()]


def get_current_pair(
    week: int,
    day_key: str,
    dt: Optional[datetime] = None,
) -> Optional[Dict[str, str]]:
    """Находит пару, которая идёт в данный момент."""
    if dt is None:
        dt = moscow_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=MSK)
    else:
        dt = dt.astimezone(MSK)

    current_time = dt.time().replace(tzinfo=None)
    schedule = SCHEDULES.get(week, {}).get(day_key, [])

    for pair in schedule:
        try:
            start_str, end_str = pair["time"].split(" - ")

            h1, m1 = map(int, start_str.split(":"))
            h2, m2 = map(int, end_str.split(":"))

            start_time = time(h1, m1)
            end_time = time(h2, m2)

            if start_time <= current_time < end_time:
                return pair

        except (ValueError, KeyError):
            logger.exception("Ошибка в записи расписания: %s", pair)

    return None


def get_next_week_number() -> int:
    """Возвращает номер следующей учебной недели."""
    current_week = get_week_number()
    return 2 if current_week == 1 else 1


# ==================================================
# ФОРМАТИРОВАНИЕ РАСПИСАНИЯ
# ==================================================


def format_schedule(
    day_key: str,
    week: int,
    date_str: str = "",
    label: str = "",
) -> str:
    """Красиво оформляет расписание на день."""
    schedule = SCHEDULES.get(week, {}).get(day_key, [])

    full_day = DAY_FULL.get(day_key, day_key).capitalize()
    emoji = DAY_EMOJI.get(day_key, "📌")

    header = f"{emoji} <b>{full_day}</b>"

    if date_str:
        header += f"  ·  <code>{date_str}</code>"

    if label:
        header += f"  ·  {label}"

    if not schedule:
        return (
            f"{header}\n\n"
            "🎉 Выходной — пар нет\n\n"
            "Можно выдохнуть!"
        )

    lines = [header, ""]

    for index, pair in enumerate(schedule, start=1):
        lines.append(
            f"<b>{index}.</b>  <code>{pair['time']}</code>"
        )
        lines.append(f"      {pair['subject']}")

        if index < len(schedule):
            lines.append("────────────────")

    return "\n".join(lines)


# ==================================================
# КЛАВИАТУРЫ
# ==================================================


def main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    buttons = [
        [
            InlineKeyboardButton(
                "📅 Сегодня",
                callback_data="cmd_today",
            ),
            InlineKeyboardButton(
                "⏰ Сейчас",
                callback_data="cmd_now",
            ),
        ],
        [
            InlineKeyboardButton(
                "🗓 Неделя",
                callback_data="cmd_week",
            ),
            InlineKeyboardButton(
                "➡️ След. неделя",
                callback_data="cmd_next_week",
            ),
        ],
        [
            InlineKeyboardButton(
                "① 1 неделя",
                callback_data="week_1",
            ),
            InlineKeyboardButton(
                "② 2 неделя",
                callback_data="week_2",
            ),
        ],
    ]

    return InlineKeyboardMarkup(buttons)


def week_days_keyboard(week: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора дня и недели."""
    buttons = [
        [
            InlineKeyboardButton(
                "Пн",
                callback_data=f"day_{week}_пн",
            ),
            InlineKeyboardButton(
                "Вт",
                callback_data=f"day_{week}_вт",
            ),
            InlineKeyboardButton(
                "Ср",
                callback_data=f"day_{week}_ср",
            ),
            InlineKeyboardButton(
                "Чт",
                callback_data=f"day_{week}_чт",
            ),
            InlineKeyboardButton(
                "Пт",
                callback_data=f"day_{week}_пт",
            ),
        ],
        [
            InlineKeyboardButton(
                "① 1 нед.",
                callback_data="week_1",
            ),
            InlineKeyboardButton(
                "② 2 нед.",
                callback_data="week_2",
            ),
        ],
        [
            InlineKeyboardButton(
                "📅 Сегодня",
                callback_data="cmd_today",
            ),
            InlineKeyboardButton(
                "⏰ Сейчас",
                callback_data="cmd_now",
            ),
            InlineKeyboardButton(
                "🏠 Меню",
                callback_data="menu",
            ),
        ],
    ]

    return InlineKeyboardMarkup(buttons)


# ==================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ОТПРАВКИ
# ==================================================


async def show_text(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    is_callback: bool = False,
) -> None:
    """Отправляет сообщение или редактирует существующее."""
    if is_callback and update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


# ==================================================
# КОМАНДА /START
# ==================================================


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Запускает бота и подписывает пользователя на уведомления."""
    if not update.effective_chat or not update.effective_message:
        return

    chat_id = update.effective_chat.id

    # Храним подписчиков в памяти до перезапуска.
    subscribers = context.application.bot_data.setdefault(
        "subscribers",
        set(),
    )
    subscribers.add(chat_id)

    now = moscow_now()
    week = get_week_number(now)
    week_emoji = "①" if week == 1 else "②"

    text = (
        "╭─────────────────╮\n"
        "│ 📚 <b>Расписание РГГУ</b> │\n"
        "╰─────────────────╯\n\n"
        "<i>Это очень необычно, зайка 💗</i>\n\n"
        "Бебебе 🐰\n\n"
        f"Сейчас идёт <b>{week_emoji} неделя</b>\n"
        "Выбери, что нужно ↓"
    )

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# ==================================================
# КНОПКА «СЕГОДНЯ»
# ==================================================


async def send_today(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    is_callback: bool = False,
) -> None:
    """Показывает расписание на сегодня."""
    now = moscow_now()

    week = get_week_number(now)
    day_key = get_day_key(now)
    date_str = now.strftime("%d.%m.%Y")

    text = format_schedule(
        day_key,
        week,
        date_str,
        "сегодня",
    )

    text += (
        "\n\n────────────────\n"
        f"🕐 {now.strftime('%H:%M')} МСК"
        f" · неделя {week}"
    )

    await show_text(
        update,
        text,
        main_keyboard(),
        is_callback,
    )


# ==================================================
# КНОПКА «СЕЙЧАС»
# ==================================================


async def send_now(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    is_callback: bool = False,
) -> None:
    """Показывает текущую пару или сообщает, что пар нет."""
    now = moscow_now()

    week = get_week_number(now)
    day_key = get_day_key(now)

    pair = get_current_pair(
        week,
        day_key,
        now,
    )

    day_name = DAY_FULL.get(day_key, day_key).capitalize()
    emoji = DAY_EMOJI.get(day_key, "📌")

    if pair:
        text = (
            "⏰ <b>Сейчас идёт пара</b>\n\n"
            f"┌ <code>{pair['time']}</code>\n"
            f"└ <b>{pair['subject']}</b>\n\n"
            "────────────────\n"
            f"{emoji} {day_name}"
            f" · неделя {week}"
            f" · {now.strftime('%H:%M')} МСК"
        )
    else:
        text = (
            "☕ <b>Сейчас пары нет</b>\n\n"
            "Можно выдохнуть и отдохнуть 💗\n\n"
            "────────────────\n"
            f"{emoji} {day_name}"
            f" · неделя {week}"
            f" · {now.strftime('%H:%M')} МСК"
        )

    await show_text(
        update,
        text,
        main_keyboard(),
        is_callback,
    )


# ==================================================
# КНОПКА «НЕДЕЛЯ»
# ==================================================


async def send_week(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    week: Optional[int] = None,
    is_callback: bool = False,
) -> None:
    """Показывает меню выбранной недели."""
    if week is None:
        week = get_week_number()

    if week not in SCHEDULES:
        week = get_week_number()

    emoji = "①" if week == 1 else "②"

    text = (
        f"{emoji} <b>Неделя {week}</b>\n\n"
        "Выбери день ↓"
    )

    await show_text(
        update,
        text,
        week_days_keyboard(week),
        is_callback,
    )


# ==================================================
# ОБРАБОТЧИКИ КНОПОК
# ==================================================


async def handle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Обрабатывает нажатия на кнопки."""
    query = update.callback_query

    if not query:
        return

    await query.answer()

    data = query.data or ""

    if data == "menu":
        now = moscow_now()
        week = get_week_number(now)
        week_emoji = "①" if week == 1 else "②"

        text = (
            "╭─────────────────╮\n"
            "│ 📚 <b>Расписание РГГУ</b> │\n"
            "╰─────────────────╯\n\n"
            "<i>Это очень необычно, зайка 💗</i>\n\n"
            "Бебебе 🐰\n\n"
            f"Сейчас идёт <b>{week_emoji} неделя</b>\n"
            "Выбери, что нужно ↓"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
        return

    if data == "cmd_today":
        await send_today(
            update,
            context,
            is_callback=True,
        )
        return

    if data == "cmd_now":
        await send_now(
            update,
            context,
            is_callback=True,
        )
        return

    if data == "cmd_week":
        await send_week(
            update,
            context,
            is_callback=True,
        )
        return

    if data == "cmd_next_week":
        next_week = get_next_week_number()

        await send_week(
            update,
            context,
            week=next_week,
            is_callback=True,
        )
        return

    if data in ("week_1", "week_2"):
        week = int(data.split("_")[1])

        await send_week(
            update,
            context,
            week=week,
            is_callback=True,
        )
        return

    if data.startswith("day_"):
        parts = data.split("_", 2)

        if len(parts) != 3:
            return

        try:
            week = int(parts[1])
        except ValueError:
            return

        day_key = parts[2]

        if week not in SCHEDULES or day_key not in DAY_FULL:
            return

        text = format_schedule(
            day_key,
            week,
            label=f"неделя {week}",
        )

        text += f"\n\n────────────────\nНеделя {week}"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=week_days_keyboard(week),
        )
        return


# ==================================================
# ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
# ==================================================


async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Позволяет пользоваться ботом текстовыми командами."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()

    if text in ("сегодня", "today"):
        await send_today(update, context)

    elif text in ("сейчас", "now"):
        await send_now(update, context)

    elif text in ("неделя", "week"):
        await send_week(update, context)

    elif text in (
        "след. неделя",
        "следующая неделя",
        "след неделя",
        "next week",
    ):
        await send_week(
            update,
            context,
            week=get_next_week_number(),
        )

    elif text in ("1 неделя", "1неделя"):
        await send_week(update, context, week=1)

    elif text in ("2 неделя", "2неделя"):
        await send_week(update, context, week=2)

    else:
        await update.message.reply_text(
            "👇 Используй кнопки меню",
            reply_markup=main_keyboard(),
        )


# ==================================================
# ЕЖЕДНЕВНЫЕ УВЕДОМЛЕНИЯ
# ==================================================


async def daily_schedule_job(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Рассылает расписание подписчикам."""
    subscribers = context.application.bot_data.get(
        "subscribers",
        set(),
    )

    if not subscribers:
        return

    now = moscow_now()
    week = get_week_number(now)
    day_key = get_day_key(now)
    date_str = now.strftime("%d.%m.%Y")

    text = format_schedule(
        day_key,
        week,
        date_str,
        "сегодня",
    )

    text += (
        "\n\n────────────────\n"
        "🔔 <b>Ежедневное напоминание</b>"
        f"\nНеделя {week}"
        f" · {now.strftime('%H:%M')} МСК"
    )

    # Копируем набор, чтобы безопасно обрабатывать подписчиков.
    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )

        except Exception:
            logger.exception(
                "Не удалось отправить сообщение пользователю %s",
                chat_id,
            )


# ==================================================
# ЗАПУСК БОТА
# ==================================================


def main() -> None:
    """Создаёт приложение и запускает бота."""
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN. "
            "Добавь токен в переменные окружения хостинга."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("today", send_today)
    )

    app.add_handler(
        CommandHandler("now", send_now)
    )

    app.add_handler(
        CommandHandler("week", send_week)
    )

    app.add_handler(
        CallbackQueryHandler(handle_callback)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    if app.job_queue:
        for index, notify_time in enumerate(NOTIFY_TIMES):
            app.job_queue.run_daily(
                daily_schedule_job,
                time=notify_time,
                name=f"daily_schedule_{index}",
            )

        logger.info(
            "Ежедневные уведомления включены: "
            "07:30 и 20:00 по Москве."
        )

    else:
        logger.error(
            "JobQueue недоступен. Установи "
            "python-telegram-bot[job-queue]."
        )

    logger.info("Бот запускается...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()