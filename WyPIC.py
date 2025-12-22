import asyncio
import os
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
        "title": "🟫 X–XII века — Древняя Русь",
        "text": (
            "Чёрная металлургия носила ремесленный характер.\n\n"
            "Использовались домницы, болотная руда и ручной труд кузнецов. "
            "Железо применялось для орудий труда, оружия и быта."
        ),
        "prompt": (
            "Ancient Rus X–XII century, iron smelting in bloomery furnace, "
            "old russian blacksmiths, clay furnace, fire and glowing metal, "
            "forest landscape, historical reconstruction, realistic, cinematic, 4k"
        )
    },

    "epoch_13_15": {
        "title": "🟫 XIII–XV века — Московская Русь",
        "text": (
            "Металлургия развивается вместе с ростом городов.\n\n"
            "Увеличивается производство оружия, формируются кузнечные слободы, "
            "металл становится стратегическим ресурсом."
        ),
        "prompt": (
            "Medieval Russia XIII–XV century, blacksmith settlement, iron forging, "
            "early furnaces, city outskirts, historical realism, cinematic lighting"
        )
    },

    "epoch_16_17": {
        "title": "🟫 XVI–XVII века — Мануфактуры",
        "text": (
            "Появляются первые металлургические мануфактуры.\n\n"
            "Используются водяные колёса, усиливается государственный контроль, "
            "производство выходит за рамки ремесла."
        ),
        "prompt": (
            "Russia XVI–XVII century, early iron manufactory, water wheel, "
            "industrial furnaces, workers, realistic historical scene, 4k"
        )
    },

    "epoch_18": {
        "title": "🟫 XVIII век — Урал",
        "text": (
            "Формируется крупная промышленная металлургия.\n\n"
            "Уральские заводы, доменные печи, массовое производство чугуна. "
            "Россия — лидер Европы по выплавке железа."
        ),
        "prompt": (
            "Russia XVIII century, Ural ironworks, blast furnace, industrial scale, "
            "smoke, fire, workers, Demidov factories, cinematic realism, 4k"
        )
    }
}

# =============================
# KEYBOARDS
# =============================

epoch_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="X–XII век", callback_data="epoch_10_12")],
        [InlineKeyboardButton(text="XIII–XV век", callback_data="epoch_13_15")],
        [InlineKeyboardButton(text="XVI–XVII век", callback_data="epoch_16_17")],
        [InlineKeyboardButton(text="XVIII век", callback_data="epoch_18")]
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

    await message.answer(
        "🏭 История чёрной металлургии в России (X–XVIII вв.)\n\n"
        "Выбери эпоху:",
        reply_markup=epoch_kb
    )

@dp.callback_query(F.data.startswith("epoch_"))
async def epoch_handler(callback: CallbackQuery):
    epoch = EPOCHS.get(callback.data)
    if not epoch:
        await callback.answer("Ошибка")
        return

    await callback.message.answer("⏳ Генерирую изображение...")

    model = await get_model(callback.from_user.id)
    image_url = await generate_image(epoch["prompt"], model)

    if image_url == "ERROR":
        await callback.message.answer("Ошибка генерации изображения")
        return

    await callback.message.answer_photo(
        photo=image_url,
        caption=f"{epoch['title']}\n\n{epoch['text']}"
    )

    await callback.answer()

# =============================
# MAIN
# =============================

async def main():
    await init_db()
    print("BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())