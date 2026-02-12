import os
import json
import asyncio
import hmac
import hashlib
import urllib.parse
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
if not BOT_TOKEN:
    print("BOT_TOKEN не найден в переменных окружения!")

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
    print("Google Sheets подключена")
except Exception as e:
    print(f"Ошибка подключения Google Sheets: {str(e)}")
    worksheet = None

# ─── Валидация initData ────────────────────────────────────────────────
def validate_and_extract_user(init_data_raw: str, bot_token: str):
    if not init_data_raw or not bot_token:
        return {"valid": False, "user_id": None, "username": None, "error": "Нет initData или токена"}

    parsed = urllib.parse.parse_qs(init_data_raw)
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        return {"valid": False, "error": "Отсутствует hash"}

    data_check_arr = [f"{k}={v[0]}" for k, v in sorted(parsed.items())]
    data_check_string = "\n".join(data_check_arr)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    if calculated_hash != received_hash:
        return {"valid": False, "error": "Неверная подпись"}

    user_str = parsed.get("user", [None])[0]
    if user_str:
        try:
            user = json.loads(user_str)
            if "id" in user:
                return {
                    "valid": True,
                    "user_id": str(user["id"]),
                    "username": user.get("username") or "no_username",
                }
        except Exception:
            pass

    return {"valid": True, "user_id": None, "username": None}

# ─── Бот ────────────────────────────────────────────────────────────────
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
        print("Бот не запущен — BOT_TOKEN отсутствует")
        return
    bot = Bot(token=BOT_TOKEN)
    print("Бот запущен, polling...")
    await dp.start_polling(bot)

# ─── Эндпоинты ──────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "OMS Mini App Backend работает"}

@app.post("/submit")
async def submit(request: Request):
    try:
        data = await request.json()
        print("Получены данные:", json.dumps(data, ensure_ascii=False, indent=2))

        # Пытаемся получить реальные данные через валидацию
        init_data_raw = data.get("initDataRaw", "")
        validation = validate_and_extract_user(init_data_raw, BOT_TOKEN)

        user_id = validation.get("user_id") or data.get("userId", "unknown")
        username = validation.get("username") or data.get("username", "unknown")

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
            username,
            data.get("gender", "—"),
            data.get("name", "—"),
            data.get("polis", "—"),
            f"{data.get('docType', '—')} {data.get('docNumber', '—')}",
            data.get("phone", "—")
        ]

        if worksheet:
            worksheet.append_row(row)
            print("Данные записаны в таблицу")
        else:
            print("Таблица НЕ подключена — запись пропущена")

        return {"status": "success"}

    except Exception as e:
        print(f"Ошибка в /submit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



