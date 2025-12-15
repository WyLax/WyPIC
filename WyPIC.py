import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram import F
from g4f.client import Client
from g4f.client import AsyncClient
from googletrans import Translator, LANGUAGES
import aiosqlite
import os
from dotenv import load_dotenv


load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")


# g4f
client = Client()
translator = Translator()

# бот
bot = Bot(API_TOKEN)
dp = Dispatcher()

# aiosqlite
base = 'WyPIC.db'
models1 = [
    "flux",
    "flux-pro",
    "flux-realism",
    "flux-3d",
    "ProdiaStableDiffusionXL"
]
models2 = [
    "Prodia",
    "stability-ai",
    "Pixart",
    "PixartLCM"
]
models1n = [
    "Flux",
    "Flux Pro",
    "Flux Realism",
    "Flux 3D",
    "Prodia Stable Diffusion XL"
]
models2n = [
    "Prodia",
    "Stability AI",
    "Pixart",
    "Pixart LCM"
]

# -----------------------------
# sqlite
# -----------------------------

async def add_user(user_id, username, name):
    async with aiosqlite.connect(base) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, user_name, name) VALUES (?, ?, ?)",
            (user_id, username, name)
        )
        await db.commit()


async def upd_cell(user_id, column_name, value):
    async with aiosqlite.connect(base) as db:
        await db.execute(
            f'UPDATE users SET {column_name} = ? WHERE id = ?',
            (value, user_id)
        )
        await db.commit()


async def get_cell(user_id, column_name):
    async with aiosqlite.connect(base) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f"SELECT {column_name} FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[column_name]
            return None

# -----------------------------
# генерация картинки
# -----------------------------

async def generate_image(prompt, model) -> str:

    try:
        response = await client.images.async_generate(
            model = model,
            prompt = prompt,
            response_format = "url"
        )
        return response.data[0].url

    except:
        return f"Ошибка"

# -----------------------------
# генерация текста
# -----------------------------

async def generate_text(prompt: str) -> str:

    try:
        async_client = AsyncClient()
        response = await async_client.chat.completions.create(
            model = "gpt-4",
            messages = [{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    except:
        return f"Ошибка"

# -----------------------------
# перевод
# -----------------------------

async def translate_to_english(text: str) -> str:

    translation = await translator.translate(
        text,
        src='ru',
        dest='en'
    )

    return translation.text

# -----------------------------
# обработчики бота
# -----------------------------

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    await message.reply("Привет! Я WyPIC, я могу нарисовать всё что за хочешь, просто оправить мне текст\nИспользуй /models, чтобы выбрать модель")



@dp.message(Command("models"))
async def models_cmd(message: Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=models1n[i], callback_data=models1[i]),
             InlineKeyboardButton(text=models2n[i], callback_data=models2[i])]
            for i in range(len(models2))
        ] + [
            [InlineKeyboardButton(text=models1n[-1], callback_data=models1[-1])]
        ]
    )

    user_model = await get_cell(message.from_user.id, 'model')

    await message.answer(
        f"<b>Установлено:</b> <code>{user_model}</code>\n<b>Список моделей нейросетей:</b>",
        reply_markup=keyboard,
        parse_mode='html'
    )



@dp.callback_query()
async def model_click(callback: CallbackQuery):
    await add_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=models1n[i], callback_data=models1[i]),
             InlineKeyboardButton(text=models2n[i], callback_data=models2[i])]
            for i in range(len(models2))
        ] + [
            [InlineKeyboardButton(text=models1n[-1], callback_data=models1[-1])]
        ]
    )

    user_model = callback.data
    if user_model != await get_cell(callback.from_user.id, 'model'):

        await upd_cell(callback.from_user.id, 'model', user_model)

        await callback.message.edit_text(
        f"<b>Установлено:</b> <code>{user_model}</code>\n<b>Список моделей нейросетей:</b>",
        reply_markup=keyboard,
        parse_mode='html'
        )



    await callback.answer()



@dp.message()
async def handle_message(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    user_text = message.text
    gen = await message.reply("Генерирую картинку, подожди...")

    user_text = await translate_to_english(user_text)
    user_model = await get_cell(message.from_user.id, 'model')

    image_url = await generate_image(user_text, user_model)

    await gen.delete()

    if image_url.startswith("Ошибка"):
        await message.reply('Прости, я задумался, повтори свой запрос')
    else:
        try:
            await message.reply_photo(
                photo = image_url,
                caption = f'<b>Запрос:</b> <code>{user_text}</code>\n<b>Модель:</b> <code>{user_model}</code>',
                parse_mode = 'html'
            )

            await bot.send_photo(
                chat_id = '-1002283294809',
                photo = image_url,
                caption = f'<b>Запрос</b>: <code>{user_text}</code>\n<b>Модель:</b> <code>{user_model}</code>',
                parse_mode = 'html'
            )
        except:
            await message.reply('Прости, я задумался, повтори свой запрос')

# -----------------------------
# запуска бота
# -----------------------------

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)




if __name__ == "__main__":
    asyncio.run(main())


