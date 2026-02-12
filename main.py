import json
import os
from datetime import datetime
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from gspread import Client, Worksheet
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI(title="OMS Mini App Backend")

# ─── КОНФИГ ─── ВСЕ ИЗМЕНЕНИЯ ТОЛЬКО ЗДЕСЬ
BOT_TOKEN = "8270215421:AAFkXC5SUASL5EtcxFLDTF0Ez04CvRlRnxw"  # ← твой токен
SHEET_URL = "https://docs.google.com/spreadsheets/d/1W6nk5COB4vLQFPzK4upA6wuGT7Q0_3NRYMjEdTxHxZQ/edit?gid=0#gid=0/edit"  # ← URL твоей таблицы
CREDENTIALS_FILE = "credentials.json"  # положи файл рядом с main.py
SUPPORT_USERNAME = "dimaaaaaaaaaaa_bot"  # ← без @

bot = Bot(token=BOT_TOKEN)
router = Router()

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
gc = gspread.authorize(creds)
worksheet = gc.open_by_url(SHEET_URL).sheet1

@app.get("/")
async def root():
    return {"message": "OMS Mini App Backend работает. Отправь /start боту в Telegram."}

@app.post("/submit")
async def submit_form(request: Request):
    try:
        data = await request.json()

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("userId", ""),
            data.get("username", ""),
            data.get("gender", ""),
            data.get("name", ""),
            data.get("polis", ""),
            f"{data.get('documentType', '')} {data.get('documentNumber', '')}",
            data.get("phone", "")
        ]

        worksheet.append_row(row)

        # Опционально — уведомление в группу
        # await bot.send_message(GROUP_ID, f"Новая регистрация: {data.get('name')}")

        return {"status": "success"}
    except Exception as e:
        print("Ошибка:", e)
        raise HTTPException(status_code=500, detail="Ошибка сервера")

@router.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть анкету ОМС",
            web_app=WebAppInfo(url="https://oms-mini-app-frontend.vercel.app/")  # ← локальный адрес твоего фронтенда
        )
    ]])

    await message.answer(
        "👋 Добро пожаловать в ОМС Онлайн!\n\n"
        "Нажмите кнопку ниже, чтобы заполнить анкету.",
        reply_markup=kb,
        parse_mode="HTML"
    )

dp = Dispatcher()
dp.include_router(router)

# Запуск бота в отдельном потоке (чтобы FastAPI работал параллельно)
async def run_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)