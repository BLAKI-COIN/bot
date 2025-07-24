import logging
import sqlite3
import random
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("data/database.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0
)""")
conn.commit()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0)", (user_id, None))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 1000)", (message.from_user.id, message.from_user.username))
    conn.commit()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    await message.answer("Добро пожаловать в BLAKI Bot!", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "balance")
async def balance_button(callback_query: types.CallbackQuery):
    balance = get_balance(callback_query.from_user.id)
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, f"💰 Ваш баланс: {balance} BLAKI")

@dp.message_handler(commands=["me"])
async def my_balance(message: types.Message):
    balance = get_balance(message.from_user.id)
    await message.reply(f"💰 Ваш баланс: {balance} BLAKI")

@dp.message_handler(commands=["pay"])
async def pay_user(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        return await message.reply("Использование: /pay @username сумма")
    username = args[1].replace("@", "")
    try:
        amount = int(args[2])
    except ValueError:
        return await message.reply("Сумма должна быть числом.")

    sender_id = message.from_user.id
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    receiver = cursor.fetchone()
    if not receiver:
        return await message.reply("Пользователь не найден.")
    if get_balance(sender_id) < amount:
        return await message.reply("Недостаточно средств.")
    update_balance(sender_id, -amount)
    update_balance(receiver[0], amount)
    await message.reply(f"✅ Переведено {amount} BLAKI пользователю @{username}")

@dp.message_handler(commands=["give", "take"])
async def admin_balance_control(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) != 3:
        return await message.reply("Использование: /give @username сумма или /take @username сумма")
    username = args[1].replace("@", "")
    try:
        amount = int(args[2])
    except ValueError:
        return await message.reply("Сумма должна быть числом.")
    if message.text.startswith("/take"):
        amount = -amount
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        return await message.reply("Пользователь не найден.")
    update_balance(user[0], amount)
    await message.reply(f"Готово. Баланс пользователя @{username} обновлён.")

@dp.message_handler(commands=["coinflip"])
async def coinflip(message: types.Message):
    args = message.text.split()
    if len(args) != 3:
        return await message.reply("Использование: /coinflip @username сумма")
    opponent_username = args[1].replace("@", "")
    try:
        amount = int(args[2])
    except ValueError:
        return await message.reply("Сумма должна быть числом.")

    if get_balance(message.from_user.id) < amount:
        return await message.reply("У вас недостаточно средств для ставки.")
    await message.reply("Монета крутится...")
    await asyncio.sleep(2)
    result = random.choice(["W", "B"])
    if result == "W":
        await message.answer("🎲 Выпало: ⚪️ W
(анимация будет позже)")
    else:
        await message.answer("🎲 Выпало: ⚫️ B
(анимация будет позже)")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)