import os
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from database import (
    init_db,
    ensure_user,
    get_balance,
    add_balance,
    set_balance,
    get_recent_transactions,
    add_free_spins,
    get_setting,
    set_setting,
)

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
MINIAPP_URL = "https://YOUR-MINIAPP.vercel.app"
ADMINS = {int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip().isdigit()}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
init_db()

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)


def menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🎰 Открыть слот", web_app=WebAppInfo(url=MINIAPP_URL)),
        InlineKeyboardButton("💰 Баланс", callback_data="show_balance"),
        InlineKeyboardButton("📜 История", callback_data="show_history"),
    )
    return kb


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    ensure_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name or "")
    jackpot = float(get_setting("jackpot_pool", "0"))
    rtp = get_setting("slot_rtp", "96")
    text = (
        "🎰 <b>Diamond | Fortune BOT</b>\n\n"
        "Главное меню слота готово.\n"
        f"RTP: <b>{rtp}%</b>\n"
        f"Jackpot Pool: <b>{jackpot:.2f}</b>"
    )
    await message.answer(text, reply_markup=menu())


@dp.message_handler(commands=["balance"])
async def balance_cmd(message: types.Message):
    ensure_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name or "")
    await message.answer(
        f"💰 Баланс: <b>{get_balance(message.from_user.id):.2f}</b>",
        reply_markup=menu()
    )


@dp.message_handler(commands=["addtest"])
async def addtest_cmd(message: types.Message):
    ensure_user(message.from_user.id, message.from_user.username or "", message.from_user.first_name or "")
    new_balance = add_balance(message.from_user.id, 25, "test_topup", "manual test topup")
    await message.answer(
        f"✅ Тестовое пополнение +25\nНовый баланс: <b>{new_balance:.2f}</b>",
        reply_markup=menu()
    )


@dp.message_handler(commands=["history"])
async def history_cmd(message: types.Message):
    txs = get_recent_transactions(message.from_user.id, 10)
    if not txs:
        await message.answer("📜 История пока пустая.", reply_markup=menu())
        return

    lines = ["📜 <b>Последние операции</b>"]
    for tx in txs:
        lines.append(f"• {tx['type']}: {tx['amount']} | {tx['comment']}")
    await message.answer("\n".join(lines), reply_markup=menu())


@dp.message_handler(commands=["setrtp"])
async def setrtp_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Только для админа.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Формат: /setrtp 96")
        return

    try:
        value = float(parts[1])
    except ValueError:
        await message.answer("Нужно число.")
        return

    if value < 70 or value > 130:
        await message.answer("Допустимо от 70 до 130")
        return

    set_setting("slot_rtp", str(value))
    await message.answer(f"✅ RTP обновлён: <b>{value}%</b>")


@dp.message_handler(commands=["jackpot"])
async def jackpot_cmd(message: types.Message):
    jackpot = float(get_setting("jackpot_pool", "0"))
    await message.answer(f"🏆 Jackpot Pool: <b>{jackpot:.2f}</b>", reply_markup=menu())


@dp.message_handler(commands=["setbalance"])
async def setbalance_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Только для админа.")
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /setbalance user_id amount")
        return

    try:
        target_user_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer("Неверный формат.")
        return

    ensure_user(target_user_id)
    new_balance = set_balance(target_user_id, amount, f"admin:{message.from_user.id}")
    await message.answer(f"✅ Баланс пользователя {target_user_id}: <b>{new_balance:.2f}</b>")


@dp.message_handler(commands=["givefs"])
async def givefs_cmd(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Только для админа.")
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /givefs user_id amount")
        return

    try:
        target_user_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("Неверный формат.")
        return

    ensure_user(target_user_id)
    free_spins = add_free_spins(target_user_id, amount, f"admin:{message.from_user.id}")
    await message.answer(f"✅ Free Spins пользователя {target_user_id}: <b>{free_spins}</b>")


@dp.callback_query_handler(lambda c: c.data == "show_balance")
async def show_balance_callback(callback: types.CallbackQuery):
    balance = get_balance(callback.from_user.id)
    await callback.message.answer(f"💰 Баланс: <b>{balance:.2f}</b>", reply_markup=menu())
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "show_history")
async def show_history_callback(callback: types.CallbackQuery):
    txs = get_recent_transactions(callback.from_user.id, 10)
    if not txs:
        await callback.message.answer("📜 История пока пустая.", reply_markup=menu())
    else:
        lines = ["📜 <b>Последние операции</b>"]
        for tx in txs:
            lines.append(f"• {tx['type']}: {tx['amount']} | {tx['comment']}")
        await callback.message.answer("\n".join(lines), reply_markup=menu())
    await callback.answer()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
