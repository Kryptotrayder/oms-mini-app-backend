import os
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Google Sheets
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials

print("Начало запуска main.py")

app = FastAPI(title="OMS Mini App Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("BOT_TOKEN не найден! Использую заглушку.")
    BOT_TOKEN = "твой_токен_для_теста"

SUPPORT_USERNAME = "kmdkdooo"

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
worksheet = None

try:
    google_credentials_str = os.getenv("GOOGLE_CREDENTIALS")
    if not google_credentials_str:
        raise ValueError("GOOGLE_CREDENTIALS не найдена")

    google_credentials = json.loads(google_credentials_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
    gc = authorize(creds)

    SHEET_URL = "https://docs.google.com/spreadsheets/d/ТВОЙ_ID_ТАБЛИЦЫ/edit"  # ← ОБЯЗАТЕЛЬНО вставь свой реальный URL!
    spreadsheet = gc.open_by_url(SHEET_URL)
    worksheet = spreadsheet.sheet1
    print("Google Sheets успешно подключён")
    print(f"Название таблицы: {spreadsheet.title}")
    print(f"Количество строк: {worksheet.row_count}")
except Exception as e:
    print(f"Ошибка подключения к Google Sheets: {str(e)}")
    worksheet = None

router = Router()

@router.message(Command("start"))
async def start(message: Message):
    print(f"Получен /start от пользователя: {message.from_user.id}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть анкету ОМС",
            web_app=WebAppInfo(url="https://oms-mini-app-frontend.vercel.app")
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
    print("Бот запущен, начинаем polling...")
    await dp.start_polling(bot)

@app.get("/")
async def root():
    print("Запрос на / — всё ок")
    return {"message": "OMS Mini App Backend работает"}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
        print("Получены данные в /submit:", json.dumps(data, ensure_ascii=False, indent=2))

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("userId", "unknown"),
            data.get("username", "unknown"),
            data.get("gender", "unknown"),
            data.get("name", "unknown"),
            data.get("polis", "unknown"),
            f"{data.get('docType', 'unknown')} {data.get('docNumber', 'unknown')}",
            data.get("phone", "unknown")
        ]
        print("Строка для записи:", row)

        if worksheet is None:
            print("Таблица НЕ подключена — запись пропущена")
            return {"status": "success", "message": "Данные получены, но таблица отключена"}

        worksheet.append_row(row)
        print("Данные успешно записаны в таблицу! Строк теперь:", worksheet.row_count)

        return {"status": "success"}
    except Exception as e:
        print(f"Критическая ошибка в /submit: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
async def startup():
    print("Startup event: запускаем бота в фоне")
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    print("Запускаем uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

