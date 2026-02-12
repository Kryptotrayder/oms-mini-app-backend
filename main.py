import os
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Импорты для Google Sheets
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials

print("Начало запуска main.py")

app = FastAPI(title="OMS Mini App Backend")

# CORS — разрешаем запросы из Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для теста — потом можно ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфиг
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("ВНИМАНИЕ: BOT_TOKEN не найден! Использую заглушку (бот не запустится).")
    BOT_TOKEN = "твой_токен_для_теста_локально"

SUPPORT_USERNAME = "kmdkdooo"

# Google Sheets — инициализация
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
worksheet = None

try:
    google_credentials_str = os.getenv("GOOGLE_CREDENTIALS")
    if not google_credentials_str:
        print("GOOGLE_CREDENTIALS не найдена в переменных окружения!")
        raise ValueError("Нет GOOGLE_CREDENTIALS")

    google_credentials = json.loads(google_credentials_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
    gc = authorize(creds)

    SHEET_URL = "https://docs.google.com/spreadsheets/d/1W6nk5COB4vLQFPzK4upA6wuGT7Q0_3NRYMjEdTxHxZQ/edit?gid=0#gid=0/edit"  # ← вставь свой реальный URL таблицы
    worksheet = gc.open_by_url(SHEET_URL).sheet1
    print("Google Sheets успешно подключён")
except Exception as e:
    print(f"Ошибка подключения к Google Sheets: {e}")
    # Не крашим приложение, просто отключаем запись

# Router для бота
router = Router()

@router.message(Command("start"))
async def start(message: Message):
    print(f"Получен /start от пользователя: {message.from_user.id}")
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

# Подключаем router
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
        print("Получены данные в /submit:", data)

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
            print("Таблица не подключена — запись пропущена")
        else:
            worksheet.append_row(row)
            print("Данные успешно записаны в таблицу!")

        return {"status": "success"}
    except Exception as e:
        print(f"Критическая ошибка в /submit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    print("Startup event: запускаем бота в фоне")
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    print("Запускаем uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

