from __future__ import annotations
import asyncio
import logging
import json
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sheets
from config import BOT_TOKEN, ADMIN_CHAT_ID, ADMIN_USERNAME, POLL_INTERVAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Храним ID уже уведомлённых заказов
_notified_orders: set[str] = set()


# ── Handlers ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    # Записываем дату регистрации если новый
    try:
        rows = sheets.get_all("users")
        exists = any(str(r.get("tg_user_id", "")) == str(user.id) for r in rows)
        if not exists:
            sheets.append_row("users", [
                user.id,
                user.username or "",
                user.first_name or "",
                str(date.today()),
            ])
            logger.info(f"New user: {user.id} @{user.username}")
    except Exception as e:
        logger.error(f"Error saving user: {e}")

    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Добро пожаловать в наш магазин.\n"
        "Нажми кнопку меню ниже чтобы открыть каталог.",
    )


async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    try:
        rows = sheets.get_all("orders")
    except Exception as e:
        await update.message.reply_text(f"Ошибка чтения таблицы: {e}")
        return

    if not rows:
        await update.message.reply_text("Заказов нет.")
        return

    # Последние 10 заказов
    recent = list(reversed(rows))[:10]

    for r in recent:
        order_id = str(r.get("id", ""))
        status = r.get("status", "new")
        status_emoji = {"new": "🆕", "confirmed": "✅", "done": "🎉", "cancelled": "❌"}.get(status, "❓")

        try:
            items = json.loads(r.get("items_json", "[]"))
            items_text = "\n".join(f"  • {i.get('name','?')} × {i.get('quantity',1)}" for i in items)
        except Exception:
            items_text = "—"

        text = (
            f"{status_emoji} `{order_id[-10:]}`\n"
            f"👤 {r.get('tg_username', '?')}\n"
            f"🕐 {r.get('pickup_time', '?')}\n"
            f"{items_text}\n"
            f"💰 {float(r.get('total', 0)):,.0f} Br"
        )

        keyboard = []
        if status == "new":
            keyboard = [[
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm:{order_id}"),
                InlineKeyboardButton("❌ Отменить",    callback_data=f"cancel:{order_id}"),
            ]]
        elif status == "confirmed":
            keyboard = [[
                InlineKeyboardButton("🎉 Выдан",      callback_data=f"done:{order_id}"),
                InlineKeyboardButton("❌ Отменить",    callback_data=f"cancel:{order_id}"),
            ]]

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.username != ADMIN_USERNAME:
        return

    action, order_id = query.data.split(":", 1)
    status_map = {"confirm": "confirmed", "done": "done", "cancel": "cancelled"}
    new_status = status_map.get(action)
    if not new_status:
        return

    try:
        # Найти строку заказа
        row_idx = sheets.find_row_idx("orders", 1, order_id)
        if not row_idx:
            await query.answer("Заказ не найден", show_alert=True)
            return

        # Обновить статус (колонка 7)
        sheets.update_cell("orders", row_idx, 7, new_status)

        # Уведомить клиента
        rows = sheets.get_all("orders")
        order = next((r for r in rows if str(r.get("id","")) == order_id), None)
        if order:
            tg_user_id = order.get("tg_user_id")
            if tg_user_id:
                await notify_customer(context.bot, int(tg_user_id), order_id, new_status)

    except Exception as e:
        logger.error(f"Error updating status: {e}")

    labels = {"confirmed": "✅ Подтверждён", "done": "🎉 Выдан", "cancelled": "❌ Отменён"}
    await query.edit_message_text(
        query.message.text + f"\n\n→ {labels[new_status]}",
        parse_mode="Markdown",
    )


async def notify_customer(bot, tg_user_id: int, order_id: str, status: str):
    labels = {
        "confirmed": "✅ Подтверждён — ждём вас!",
        "done":      "🎉 Выдан — спасибо за покупку!",
        "cancelled": "❌ Отменён",
    }
    label = labels.get(status)
    if not label:
        return
    try:
        await bot.send_message(
            chat_id=tg_user_id,
            text=f"Заказ `{order_id[-10:]}`: {label}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to notify customer {tg_user_id}: {e}")


# ── Polling новых заказов ─────────────────────────────────

async def poll_new_orders(bot):
    """Проверяет новые заказы каждые POLL_INTERVAL секунд."""
    global _notified_orders

    # При старте загружаем существующие заказы чтобы не слать уведомления о старых
    try:
        rows = sheets.get_all("orders")
        for r in rows:
            _notified_orders.add(str(r.get("id", "")))
        logger.info(f"Loaded {len(_notified_orders)} existing orders")
    except Exception as e:
        logger.error(f"Error loading existing orders: {e}")

    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            rows = sheets.get_all("orders")
            for r in rows:
                order_id = str(r.get("id", ""))
                if not order_id or order_id in _notified_orders:
                    continue
                if r.get("status") != "new":
                    _notified_orders.add(order_id)
                    continue

                # Новый заказ — уведомляем админа
                try:
                    items = json.loads(r.get("items_json", "[]"))
                    items_text = "\n".join(
                        f"  • {i.get('name','?')} × {i.get('quantity',1)} — {float(i.get('price',0)) * int(i.get('quantity',1)):,.0f} Br"
                        for i in items
                    )
                except Exception:
                    items_text = "—"

                text = (
                    f"🛍 *Новый заказ* `{order_id[-10:]}`\n\n"
                    f"👤 {r.get('tg_username','?')}\n"
                    f"🕐 {r.get('pickup_time','?')}\n\n"
                    f"*Состав:*\n{items_text}\n\n"
                    f"💰 *Итого: {float(r.get('total',0)):,.0f} Br*"
                )

                keyboard = [[
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm:{order_id}"),
                    InlineKeyboardButton("❌ Отменить",    callback_data=f"cancel:{order_id}"),
                ]]

                await bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                _notified_orders.add(order_id)
                logger.info(f"Notified admin about order {order_id}")

        except Exception as e:
            logger.error(f"Error polling orders: {e}")


# ── Entry point ───────────────────────────────────────────

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    async with app:
        await app.start()
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
        logger.info("Bot started. Polling for new orders every %ds", POLL_INTERVAL)

        # Запускаем polling заказов параллельно
        await poll_new_orders(app.bot)


if __name__ == "__main__":
    asyncio.run(main())
