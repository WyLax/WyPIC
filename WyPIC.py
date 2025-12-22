import asyncio
import os
import random
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

import aiosqlite
from g4f.client import Client, AsyncClient

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
async_client = AsyncClient()

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
        async with db.execute("SELECT model FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "flux"

# =============================
# AI GENERATION
# =============================
async def generate_image(prompt: str, model: str) -> str:
    try:
        response = await client.images.async_generate(
            model=model,
            prompt=prompt,
            response_format="url"
        )
        return response.data[0].url
    except:
        return None

async def generate_text(epoch_hint: str, epoch_name: str) -> str:
    try:
        response = await async_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты историк. Пиши краткое информативное описание "
                        "развития черной металлургии в России строго для заданной эпохи. "
                        "НЕ упоминай другие века или эпохи."
                    )
                },
                {
                    "role": "user",
                    "content": f"Опиши металлургию России для эпохи {epoch_name} ({epoch_hint})"
                }
            ]
        )
        return response.choices[0].message.content
    except:
        return "🤔 Я задумалась и пока не могу ответить, попробуй ещё раз."

# =============================
# EPOCH DATA
# =============================
EPOCHS = {
    "epoch_10_12": {
        "hint": "домницы, болотные руды, ручной труд",
        "answer": "X–XII век",
        "image_prompt": "Ancient Rus, bloomery furnace, blacksmiths, clay furnace, forest, realistic, cinematic, 4k"
    },
    "epoch_13_15": {
        "hint": "развитие городов, кузнечные слободы, производство оружия",
        "answer": "XIII–XV век",
        "image_prompt": "Medieval Russia, blacksmith settlement, iron forging, early furnaces, historical realism, cinematic lighting"
    },
    "epoch_16_17": {
        "hint": "первые мануфактуры, водяные колеса, контроль государства",
        "answer": "XVI–XVII век",
        "image_prompt": "Russia early modern period, iron manufactory, water wheel, workers, industrial furnaces, realistic, 4k"
    },
    "epoch_18": {
        "hint": "Урал, доменные печи, промышленный масштаб",
        "answer": "XVIII век",
        "image_prompt": "Russia 18th century, Ural ironworks, blast furnace, smoke, fire, industrial scale, cinematic realism, 4k"
    }
}

# =============================
# QUIZ STATE
# =============================
current_epoch = {}

# =============================
# KEYBOARDS
# =============================
def get_quiz_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="X–XII век", callback_data="answer_10_12")],
            [InlineKeyboardButton(text="XIII–XV век", callback_data="answer_13_15")],
            [InlineKeyboardButton(text="XVI–XVII век", callback_data="answer_16_17")],
            [InlineKeyboardButton(text="XVIII век", callback_data="answer_18")]
        ]
    )

def get_next_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Следующий вопрос", callback_data="next_quiz")]
        ]
    )

# =============================
# HANDLERS
# =============================
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer("👋 Привет! Добро пожаловать в викторину по металлургии России. Попробуй угадать эпоху!")
    await send_random_quiz(message)

async def send_random_quiz(message: Message):
    epoch_key = random.choice(list(EPOCHS.keys()))
    current_epoch[message.from_user.id] = epoch_key
    epoch = EPOCHS[epoch_key]
    model = await get_model(message.from_user.id)

    text = await generate_text(epoch["hint"], epoch["answer"])
    image_url = await generate_image(epoch["image_prompt"], model)

    if image_url is None:
        await message.answer("🤔 Я задумалась и пока не могу сгенерировать картинку, попробуй ещё раз.")
        return

    await message.answer_photo(photo=image_url, caption=text, reply_markup=get_quiz_kb())

@dp.callback_query(F.data.startswith("answer_"))
async def answer_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    correct_key = current_epoch.get(user_id)

    if not correct_key:
        await callback.answer("Начни с /start")
        return

    user_answer = callback.data.replace("answer_", "")
    correct_answer_key = correct_key.replace("epoch_", "")

    if user_answer == correct_answer_key:
        await callback.message.answer("✅ Правильно!")
    else:
        right = EPOCHS[correct_key]["answer"]
        await callback.message.answer(f"❌ Неверно.\nПравильный ответ: {right}")

    await callback.message.answer("Хочешь попробовать ещё?", reply_markup=get_next_kb())
    await callback.answer()

@dp.callback_query(F.data == "next_quiz")
async def next_quiz(callback: CallbackQuery):
    await send_random_quiz(callback.message)
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