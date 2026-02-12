import os
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

print("Начало запуска main.py")

app = FastAPI(title="OMS Mini App Backend")

# CORS — разрешаем запросы из Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для теста — потом можно ограничить ["https://*.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфиг
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("ВНИМАНИЕ: BOT_TOKEN не найден в переменных окружения! Использую заглушку.")
    BOT_TOKEN = "твой_токен_для_теста_локально"

SUPPORT_USERNAME = "kmdkdooo"

# Создаём router ПЕРЕД использованием
router = Router()

@app.get("/")
async def root():
    print("Запрос на / — всё ок")
    return {"message": "OMS Mini App Backend работает"}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
        print("Получены данные в /submit:", data)
        # Здесь будет запись в таблицу (пока заглушка)
        return {"status": "success", "message": "Данные получены"}
    except Exception as e:
        print("Ошибка в /submit:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.message(Command("start"))
async def start(message: Message):
    print("Получен /start от пользователя:", message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть анкету ОМС",
            web_app=WebAppInfo(url="https://oms-mini-app-frontend.vercel.app")  # ← твой URL фронтенда
        )
    ]])

    await message.answer(
        "👋 Добро пожаловать в ОМС Онлайн!\n\n"
        "Нажмите кнопку ниже, чтобы заполнить анкету.",
        reply_markup=kb
    )

# Подключаем router к диспетчеру ПОСЛЕ его создания
dp = Dispatcher()
dp.include_router(router)

async def run_bot():
    bot = Bot(token=BOT_TOKEN)
    print("Бот запущен, начинаем polling...")
    await dp.start_polling(bot)

@app.on_event("startup")
async def startup():
    print("Startup event: запускаем бота в фоне")
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    print("Запускаем uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
