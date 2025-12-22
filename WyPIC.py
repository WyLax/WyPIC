import asyncio
import os
import random
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery
)

import aiosqlite
from g4f.client import Client

# =============================
# ENV
# =============================

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

# =============================
# BOT / CLIENT
# =============================

bot = Bot(API_TOKEN)
dp = Dispatcher()
client = Client()

# =============================
# DATABASE
# =============================

DB_NAME = "WyPIC.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_name TEXT,
                name TEXT,
                model TEXT DEFAULT 'flux'
            )
        """)
        await db.commit()

async def add_user(user_id, username, name):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, user_name, name) VALUES (?, ?, ?)",
            (user_id, username, name)
        )
        await db.commit()

async def get_model(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT model FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "flux"

# =============================
# IMAGE GENERATION
# =============================

async def generate_image(prompt: str, model: str) -> str:
    try:
        response = await client.images.async_generate(
            model=model,
            prompt=prompt,
            response_format="url"
        )
        return response.data[0].url
    except Exception:
        return "ERROR"

# =============================
# EPOCH DATA
# =============================

EPOCHS = {
    "epoch_10_12": {
        "answer": "X–XII век",
        "text": (
            "Металлургия носила ремесленный характер. "
            "Использовались домницы, болотная руда, ручной труд кузнецов."
        ),
        "prompt": (
            "Ancient Rus X–XII century, iron smelting in bloomery furnace, "
            "old russian blacksmiths, clay furnace, fire and glowing metal, "
            "forest landscape, historical reconstruction, realistic, cinematic, 4k"
        )
    },
    "epoch_13_15": {
        "answer": "XIII–XV век",
        "text": (
            "Производство железа расширяется вместе с ростом городов. "
            "Формируются кузнечные слободы, возрастает спрос на оружие."
        ),
        "prompt": (
            "Medieval Russia XIII–XV century, blacksmith settlement, iron forging, "
            "early furnaces, historical realism, cinematic lighting"
        )
    },
    "epoch_16_17": {
        "answer": "XVI–XVII век",
        "text": (
            "Появляются первые мануфактуры, используются водяные механизмы. "
            "Металлургия выходит за рамки ремесла."
        ),
        "prompt": (
            "Russia XVI–XVII century, early iron manufactory, water wheel, "
            "industrial furnaces, workers, realistic historical scene, 4k"
        )
    },
    "epoch_18": {
        "answer": "XVIII век",
        "text": (
            "Формируется крупная промышленная металлургия. "
            "Уральские заводы и доменные печи обеспечивают массовую выплавку чугуна."
        ),
        "prompt": (
            "Russia XVIII century, Ural ironworks, blast furnace, industrial scale, "
            "smoke, fire, workers, Demidov factories, cinematic realism, 4k"
        )
    }
}

# =============================
# QUIZ STATE
# =============================

current_epoch = {}

# =============================
# KEYBOARDS
# =============================

quiz_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="X–XII век", callback_data="answer_10_12")],
        [InlineKeyboardButton(text="XIII–XV век", callback_data="answer_13_15")],
        [InlineKeyboardButton(text="XVI–XVII век", callback_data="answer_16_17")],
        [InlineKeyboardButton(text="XVIII век", callback_data="answer_18")]
    ]
)

next_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Следующий вопрос", callback_data="next_quiz")]
    ]
)

# =============================
# HANDLERS
# =============================

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    epoch_key = random.choice(list(EPOCHS.keys()))
    current_epoch[message.from_user.id] = epoch_key
    epoch = EPOCHS[epoch_key]

    await message.answer("🧠 Угадай эпоху по описанию и изображению:")

    model = await get_model(message.from_user.id)
    image_url = await generate_image(epoch["prompt"], model)

    if image_url == "ERROR":
        await message.answer("Ошибка генерации изображения")
        return

    await message.answer_photo(
        photo=image_url,
        caption=epoch["text"]
    )

    await message.answer(
        "Какой это период?",
        reply_markup=quiz_kb
    )

@dp.callback_query(F.data.startswith("answer_"))
async def answer_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    correct_key = current_epoch.get(user_id)

    if not correct_key:
        await callback.answer("Начни с /start")
        return

    user_answer = callback.data.replace("answer_", "")
    correct_answer = correct_key.replace("epoch_", "")

    if user_answer == correct_answer:
        await callback.message.answer("✅ Правильно!")
    else:
        right = EPOCHS[correct_key]["answer"]
        await callback.message.answer(
            f"❌ Неверно.\nПравильный ответ: {right}"
        )

    await callback.message.answer(
        "Хочешь попробовать ещё?",
        reply_markup=next_kb
    )

    await callback.answer()

@dp.callback_query(F.data == "next_quiz")
async def next_quiz(callback: CallbackQuery):
    await start_cmd(callback.message)
    await callback.answer()

# =============================
# MAIN
# =============================

async def main():
    await init_db()
    print("QUIZ BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())