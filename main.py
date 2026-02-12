import os
import json
import asyncio
from datetime import datetime

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from aiogram import Bot, Dispatcher, Router
    from aiogram.filters import Command
    from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    from gspread import authorize
    from oauth2client.service_account import ServiceAccountCredentials
    print("Все импорты успешны")
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    raise

app = FastAPI(title="OMS Mini App Backend")

# Конфиг
BOT_TOKEN = os.getenv("BOT_TOKEN") or "твой_токен_для_теста"
SUPPORT_USERNAME = "kmdkdooo"

# CORS (чтобы Mini App мог слать запросы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для теста — потом можно ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "OMS Mini App Backend работает"}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
        print("Получены данные:", data)  # для логов Vercel

        # Запись в таблицу (пока заглушка — потом добавим gspread)
        return {"status": "success", "message": "Данные получены (таблица пока отключена для теста)"}
    except Exception as e:
        print("Ошибка в /submit:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть анкету ОМС",
            web_app=WebAppInfo(url="https://oms-mini-app-frontend.vercel.app")  # твой URL фронтенда
        )
    ]])

    await message.answer(
        "👋 Добро пожаловать в ОМС Онлайн!\n\n"
        "Нажмите кнопку ниже, чтобы заполнить анкету.",
        reply_markup=kb
    )

dp = Dispatcher()
dp.include_router(router)

async def run_bot():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
