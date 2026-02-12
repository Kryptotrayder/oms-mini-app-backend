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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["*"],
    max_age=600,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_USERNAME = "kmdkdooo"

# Google Sheets
worksheet = None
try:
    google_credentials_str = os.getenv("GOOGLE_CREDENTIALS")
    if not google_credentials_str:
        raise ValueError("GOOGLE_CREDENTIALS не найдена")
    
    google_credentials = json.loads(google_credentials_str)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
    gc = authorize(creds)
    
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1W6nk5COB4vLQFPzK4upA6wuGT7Q0_3NRYMjEdTxHxZQ/edit?gid=0"
    spreadsheet = gc.open_by_url(SHEET_URL)
    worksheet = spreadsheet.sheet1
    print(f"Google Sheets подключена: {spreadsheet.title} | строк: {worksheet.row_count}")
except Exception as e:
    print(f"Ошибка Google Sheets: {e}")
    worksheet = None

# ─── Бот ────────────────────────────────────────────────
router = Router()

@router.message(Command("start"))
async def start(message: Message):
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
    if not BOT_TOKEN:
        print("BOT_TOKEN отсутствует → бот не запущен")
        return
    bot = Bot(token=BOT_TOKEN)
    print("Бот запущен (polling)")
    await dp.start_polling(bot)

# ─── Эндпоинты ──────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "OMS Mini App Backend работает"}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
        print("Получены данные:", json.dumps(data, ensure_ascii=False, indent=2))

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("userId", "—"),
            data.get("username", "—"),
            data.get("firstName", "—"),
            data.get("lastName", "—"),
            data.get("gender", "—"),
            data.get("name", "—"),
            data.get("polis", "—"),
            f"{data.get('docType', '—')} {data.get('docNumber', '—')}",
            data.get("phone", "—"),
        ]

        if worksheet:
            worksheet.append_row(row)
            print(f"Записано в таблицу. Строк теперь: {worksheet.row_count}")
        else:
            print("Google Sheets НЕ подключена — данные НЕ сохранены")

        return {"status": "success"}

    except Exception as e:
        print(f"Ошибка в /submit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


