[16.10.2026 0:19] Datur: #!/usr/bin/env python3
-- coding: utf-8 --
""" Telegram-бот: Расписание РГГУ. Чередующиеся недели, расписание на сегодня и сейчас, выбор дня и ежедневные уведомления в 07:30 и 20:00 МСК. """
import json import logging import os from datetime import datetime, time from pathlib import Path from typing import Dict, List, Optional from zoneinfo import ZoneInfo
from telegram import ( Update, InlineKeyboardMarkup, InlineKeyboardButton, ) from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, )
==================== НАСТРОЙКИ ====================
MSK = ZoneInfo("Europe/Moscow")
BOT_TOKEN = os.getenv("BOT_TOKEN") if not BOT_TOKEN: raise RuntimeError( "Не задан BOT_TOKEN. Установи переменную окружения с токеном бота." )
NOTIFY_TIMES = [ time(7, 30, tzinfo=MSK), time(20, 0, tzinfo=MSK), ]
SUBSCRIBERS_FILE = Path("subscribers.json")
==================== РАСПИСАНИЕ ====================
WEEK_1: Dict[str, List[Dict[str, str]]] = { "пн": [ {"time": "9:00 - 10:00", "subject": "разговоры о важном"}, {"time": "10:15 - 11:45", "subject": "история"}, {"time": "11:55 - 13:25", "subject": "математика"}, {"time": "13:50 - 15:20", "subject": "русский язык"}, ], "вт": [ {"time": "10:15 - 11:45", "subject": "математика"}, {"time": "11:55 - 13:25", "subject": "биология"}, {"time": "13:50 - 15:20", "subject": "история"}, {"time": "15:35 - 17:05", "subject": "физика"}, ], "ср": [ {"time": "10:15 - 11:45", "subject": "информатика"}, {"time": "11:55 - 13:25", "subject": "информатика"}, {"time": "13:50 - 15:20", "subject": "литература"}, {"time": "15:35 - 17:05", "subject": "английский язык"}, ], "чт": [ {"time": "11:55 - 13:25", "subject": "обществознание"}, {"time": "13:50 - 15:20", "subject": "обществознание"}, ], "пт": [ {"time": "8:30 - 10:00", "subject": "химия"}, {"time": "10:15 - 11:45", "subject": "география"}, {"time": "11:55 - 13:25", "subject": "обж"}, {"time": "15:00 - 16:30", "subject": "физра"}, ], }
WEEK_2: Dict[str, List[Dict[str, str]]] = { "пн": [ {"time": "9:00 - 10:00", "subject": "разговоры о важном"}, {"time": "10:15 - 11:45", "subject": "литература"}, {"time": "11:55 - 13:25", "subject": "общество"}, {"time": "13:50 - 15:20", "subject": "литература"}, {"time": "15:35 - 17:05", "subject": "математика"}, ], "вт": [ {"time": "8:30 - 10:00", "subject": "русский язык"}, {"time": "10:15 - 11:45", "subject": "математика"}, {"time": "11:55 - 13:25", "subject": "информатика"}, ], "ср": [ {"time": "10:15 - 11:45", "subject": "английский язык"}, {"time": "11:55 - 13:25", "subject": "английский язык"}, {"time": "13:50 - 15:20", "subject": "математика"}, {"time": "15:35 - 17:05", "subject": "история"}, ], "чт": [ {"time": "8:30 - 10:00", "subject": "химия"}, {"time": "10:15 - 11:45", "subject": "физика"}, {"time": "11:55 - 13:25", "subject": "индивидуальный проект"}, {"time": "15:00 - 16:30", "subject": "физра"}, ], "пт": [ {"time": "10:15 - 11:45", "subject": "биология"}, {"time": "11:55 - 13:25", "subject": "обж"}, {"time": "13:50 - 15:20", "subject": "география"}, ], }
SCHEDULES = {1: WEEK_1, 2: WEEK_2}
DAY_NAMES = { 0: "пн", 1: "вт", 2: "ср", 3: "чт", 4: "пт", 5: "сб", 6: "вс", }
DAY_FULL = { "пн": "понедельник", "вт": "вторник", "ср": "среда", "чт": "четверг", "пт": "пятница", "сб": "суббота", "вс": "воскресенье", }
DAY_EMOJI = { "пн": "1️⃣", "вт": "2️⃣", "ср": "3️⃣", "чт": "4️⃣", "пт": "5️⃣", "сб": "💤", "вс": "💤", }
==================== ЛОГИРОВАНИЕ ====================
logging.basicConfig( format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, ) logger = logging.getLogger(name)
==================== ВРЕМЯ И НЕДЕЛИ ====================
def moscow_now() -> datetime: return datetime.now(MSK)
def normalize_datetime(dt: Optional[datetime] = None) -> datetime: if dt is None: return moscow_now() if dt.tzinfo is None: return dt.replace(tzinfo=MSK) return dt.astimezone(MSK)
def get_week_number(dt: Optional[datetime] = None) -> int: """ Чётная ISO-неделя = неделя 1. Нечётная ISO-неделя = неделя 2.
Если у вашей группы другая привязка недель,
[16.10.2026 0:19] Datur: измени эту функцию под учебный календарь.
"""
dt = normalize_datetime(dt)
return 1 if dt.isocalendar().week % 2 == 0 else 2
def get_next_week() -> int: return 2 if get_week_number() == 1 else 1
def get_day_key(dt: Optional[datetime] = None) -> str: dt = normalize_datetime(dt) return DAY_NAMES[dt.weekday()]
def get_current_pair( week: int, day_key: str, dt: Optional[datetime] = None, ) -> Optional[Dict[str, str]]: """Возвращает текущую пару с учётом московского времени.""" dt = normalize_datetime(dt) now = dt.time().replace(tzinfo=None)
for pair in SCHEDULES.get(week, {}).get(day_key, []):
    try:
        start_str, end_str = pair["time"].split(" - ")
        start_t = datetime.strptime(start_str, "%H:%M").time()
        end_t = datetime.strptime(end_str, "%H:%M").time()

        if start_t <= now < end_t:
            return pair
    except (ValueError, KeyError):
        logger.exception("Некорректная запись расписания: %s", pair)

return None
==================== ФОРМАТИРОВАНИЕ ====================
def format_schedule( day_key: str, week: int, date_str: str = "", label: str = "", ) -> str: schedule = SCHEDULES.get(week, {}).get(day_key, []) full_day = DAY_FULL.get(day_key, day_key).capitalize() emoji = DAY_EMOJI.get(day_key, "📌")
header = f"{emoji} <b>{full_day}</b>"
if date_str:
    header += f"  ·  <code>{date_str}</code>"
if label:
    header += f"  ·  {label}"

if not schedule:
    return (
        f"{header}\n\n"
        "🎉 Выходной — пар нет\n\n"
        "Можно выдохнуть"
    )

lines = [header, ""]
for i, pair in enumerate(schedule, 1):
    lines.append(f"<b>{i}.</b>  <code>{pair['time']}</code>")
    lines.append(f"      {pair['subject']}")
    if i < len(schedule):
        lines.append("────────────────")

return "\n".join(lines)
def main_text() -> str: week = get_week_number() emoji = "①" if week == 1 else "②"
return (
    "╭─────────────────╮\n"
    "│  📚  <b>Расписание РГГУ</b>  │\n"
    "╰─────────────────╯\n\n"
    "<i>? это очень необычно зайка</i>\n\n"
    "бебебе\n\n"
    f"Сейчас идёт <b>{emoji} неделя</b>\n"
    "Выбери, что нужно ↓"
)
==================== КЛАВИАТУРЫ ====================
def main_keyboard() -> InlineKeyboardMarkup: return InlineKeyboardMarkup([ [ InlineKeyboardButton("📅 Сегодня", callback_data="cmd_today"), InlineKeyboardButton("⏰ Сейчас", callback_data="cmd_now"), ], [ InlineKeyboardButton("🗓 Неделя", callback_data="cmd_week"), InlineKeyboardButton("➡️ След. неделя", callback_data="cmd_next_week"), ], [ InlineKeyboardButton("① 1 неделя", callback_data="week_1"), InlineKeyboardButton("② 2 неделя", callback_data="week_2"), ], ])
def week_days_keyboard(week: int) -> InlineKeyboardMarkup: return InlineKeyboardMarkup([ [ InlineKeyboardButton("Пн", callback_data=f"day_{week}пн"), InlineKeyboardButton("Вт", callback_data=f"day{week}вт"), InlineKeyboardButton("Ср", callback_data=f"day{week}ср"), InlineKeyboardButton("Чт", callback_data=f"day{week}чт"), InlineKeyboardButton("Пт", callback_data=f"day{week}_пт"), ], [ InlineKeyboardButton("① 1 нед.", callback_data="week_1"), InlineKeyboardButton("② 2 нед.", callback_data="week_2"), ], [ InlineKeyboardButton("📅 Сегодня", callback_data="cmd_today"), InlineKeyboardButton("⏰ Сейчас", callback_data="cmd_now"), InlineKeyboardButton("🏠 Меню", callback_data="menu"), ], ])
==================== ПОДПИСЧИКИ ====================
def load_subscribers() -> set[int]: """Загружает подписчиков из JSON после перезапуска.""" try: if SUBSCRIBERS_FILE.exists(): data = json.loads( SUBSCRIBERS_FILE.read_text(encoding="utf-8") ) return {int(chat_id) for chat_id in data} except (OSError, ValueError, TypeError): logger.exception("Не удалось загрузить подписчиков")
return set()
def save_subscribers(subscribers: set[int]) -> None: """Сохраняет список подписчиков на диск.""" try: SUBSCRIBERS_FILE.write_text( json.dumps(sorted(subscribers), ensure_ascii=False), encoding="utf-8", ) except OSError: logger.exception("Не удалось сохранить подписчиков")
==================== ОТПРАВКА РАСПИСАНИЯ ====================
[16.10.2026 0:19] Datur: async def send_today( update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False, ) -> None: now = moscow_now() week = get_week_number(now) day_key = get_day_key(now)
text = format_schedule(
    day_key, week, now.strftime("%d.%m"), "сегодня"
)
text += (
    f"\n\n────────────────\n"
    f"🕐 {now.strftime('%H:%M')} · неделя {week}"
)

if is_callback:
    await update.callback_query.edit_message_text(
        text, parse_mode="HTML", reply_markup=main_keyboard()
    )
else:
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=main_keyboard()
    )
async def send_now( update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False, ) -> None: now = moscow_now() week = get_week_number(now) day_key = get_day_key(now) pair = get_current_pair(week, day_key, now)
day_name = DAY_FULL.get(day_key, day_key).capitalize()
emoji = DAY_EMOJI.get(day_key, "📌")

if pair:
    text = (
        "⏰ <b>Сейчас идёт пара</b>\n\n"
        f"┌ <code>{pair['time']}</code>\n"
        f"└ <b>{pair['subject']}</b>\n\n"
        "────────────────\n"
        f"{emoji} {day_name} · неделя {week} · "
        f"{now.strftime('%H:%M')} МСК"
    )
else:
    text = (
        "☕ <b>Сейчас пары нет</b>\n\n"
        "Можно выдохнуть и отдохнуть\n\n"
        "────────────────\n"
        f"{emoji} {day_name} · неделя {week} · "
        f"{now.strftime('%H:%M')} МСК"
    )

if is_callback:
    await update.callback_query.edit_message_text(
        text, parse_mode="HTML", reply_markup=main_keyboard()
    )
else:
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=main_keyboard()
    )
async def send_week( update: Update, context: ContextTypes.DEFAULT_TYPE, week: Optional[int] = None, is_callback: bool = False, ) -> None: if week not in (1, 2): week = get_week_number()
emoji = "①" if week == 1 else "②"
text = f"{emoji} <b>Неделя {week}</b>\n\nВыбери день ↓"
markup = week_days_keyboard(week)

if is_callback:
    await update.callback_query.edit_message_text(
        text, parse_mode="HTML", reply_markup=markup
    )
else:
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=markup
    )
==================== КОМАНДЫ И КНОПКИ ====================
async def start( update: Update, context: ContextTypes.DEFAULT_TYPE, ) -> None: chat = update.effective_chat if chat is None or update.effective_message is None: return
subscribers = context.application.bot_data["subscribers"]
subscribers.add(chat.id)
save_subscribers(subscribers)

await update.effective_message.reply_text(
    main_text(),
    parse_mode="HTML",
    reply_markup=main_keyboard(),
)
async def handle_callback( update: Update, context: ContextTypes.DEFAULT_TYPE, ) -> None: query = update.callback_query if query is None or query.data is None: return
await query.answer()
data = query.data

if data == "menu":
    await query.edit_message_text(
        main_text(),
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
    await send_week(
        update, context, week=get_next_week(), is_callback=True
    )
    return

if data in ("week_1", "week_2"):
    week = int(data[-1])
    await send_week(update, context, week=week, is_callback=True)
    return

if data.startswith("day_"):
    try:
        _, week_str, day_key = data.split("_", 2)
        week = int(week_str)

        if week not in (1, 2) or day_key not in DAY_FULL:
            raise ValueError("Неизвестная неделя или день")

        text = format_schedule(
            day_key, week, label=f"неделя {week}"
        )
        text += f"\n\n────────────────\nнеделя {week}"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
[16.10.2026 0:19] Datur: reply_markup=week_days_keyboard(week),
        )
    except ValueError:
        await query.answer(
            "Не удалось определить день расписания.",
            show_alert=True,
        )
async def handle_text( update: Update, context: ContextTypes.DEFAULT_TYPE, ) -> None: message = update.effective_message if message is None or message.text is None: return
text = message.text.lower().strip()

if text in ("сегодня", "today"):
    await send_today(update, context)
elif text in ("сейчас", "now"):
    await send_now(update, context)
elif text == "неделя":
    await send_week(update, context)
elif text in ("след. неделя", "следующая неделя", "след неделя"):
    await send_week(update, context, week=get_next_week())
elif text in ("1 неделя", "1неделя"):
    await send_week(update, context, week=1)
elif text in ("2 неделя", "2неделя"):
    await send_week(update, context, week=2)
else:
    await message.reply_text(
        "👇 Используй кнопки",
        reply_markup=main_keyboard(),
    )
==================== ЕЖЕДНЕВНЫЕ УВЕДОМЛЕНИЯ ====================
async def daily_schedule_job( context: ContextTypes.DEFAULT_TYPE, ) -> None: subscribers = context.application.bot_data["subscribers"] if not subscribers: return
now = moscow_now()
week = get_week_number(now)
day_key = get_day_key(now)

text = format_schedule(
    day_key, week, now.strftime("%d.%m"), "сегодня"
)
text += (
    "\n\n────────────────\n"
    f"🔔 Ежедневное напоминание · неделя {week} · "
    f"{now.strftime('%H:%M')} МСК"
)

failed_chats = set()

for chat_id in list(subscribers):
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
    except Exception as exc:
        logger.warning(
            "Не удалось отправить сообщение в чат %s: %s",
            chat_id,
            exc,
        )

        # Удаляем подписчика только если бот заблокирован
        # или чат больше недоступен.
        if getattr(exc, "message", None) and (
            "blocked" in str(exc).lower()
            or "chat not found" in str(exc).lower()
        ):
            failed_chats.add(chat_id)

if failed_chats:
    subscribers.difference_update(failed_chats)
    save_subscribers(subscribers)
==================== ОБРАБОТКА ОШИБОК ====================
async def error_handler( update: object, context: ContextTypes.DEFAULT_TYPE, ) -> None: logger.error( "Ошибка при обработке обновления", exc_info=context.error, )
==================== ЗАПУСК ====================
def main() -> None: app = Application.builder().token(BOT_TOKEN).build()
app.bot_data["subscribers"] = load_subscribers()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
)
app.add_error_handler(error_handler)

if app.job_queue is not None:
    for index, notify_time in enumerate(NOTIFY_TIMES):
        app.job_queue.run_daily(
            daily_schedule_job,
            time=notify_time,
            name=f"daily_schedule_{index}",
        )

    logger.info("Уведомления запланированы на 07:30 и 20:00 МСК")
else:
    logger.error(
        "JobQueue недоступен. Установи "
        "'python-telegram-bot[job-queue]'."
    )

logger.info(
    "Бот запущен. Подписчиков: %d",
    len(app.bot_data["subscribers"]),
)

app.run_polling(allowed_updates=Update.ALL_TYPES)
if name == "main": main()
