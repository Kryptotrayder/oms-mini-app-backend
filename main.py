import os
import json
import asyncio
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция для сбора всех токенов из переменных окружения
def get_all_tokens():
    tokens = [v for k, v in os.environ.items() if k.startswith("BOT_TOKEN")]
    return tokens if tokens else [os.getenv("BOT_TOKEN")]

# Google Sheets Setup
worksheet = None
try:
    google_credentials = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, scope)
    gc = authorize(creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1W6nk5COB4vLQFPzK4upA6wuGT7Q0_3NRYMjEdTxHxZQ/edit")
    worksheet = spreadsheet.sheet1
    print("✅ Google Sheets подключена")
except Exception as e:
    print(f"❌ Ошибка Google Sheets: {e}")

def get_telegram_user(init_data_raw: str):
    if not init_data_raw:
        return None
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_raw))
        if "user" in parsed_data:
            return json.loads(parsed_data["user"])
    except:
        pass
    return None

@app.post("/check_user")
async def check_user(request: Request):
    data = await request.json()
    init_raw = data.get("initDataRaw", "")
    user = get_telegram_user(init_raw)
    
    if not user or not worksheet:
        return {"is_blocked": False}

    user_id = str(user.get("id"))
    try:
        existing_ids = worksheet.col_values(2)
        if user_id in existing_ids:
            return {"is_blocked": True}
    except:
        pass
    return {"is_blocked": False}

@app.post("/submit")
async def submit(request: Request):
    data = await request.json()
    init_raw = data.get("initDataRaw", "")
    bot_label = data.get("bot_label", "default")
    user = get_telegram_user(init_raw)
    
    user_id = str(user.get("id", "Unknown"))
    username = user.get("username", "Unknown")

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        username,
        data.get("gender", "—"),
        data.get("name", "—"),
        data.get("polis", "—"),
        f"{data.get('docType', '—')} {data.get('docNumber', '—')}",
        data.get("phone", "—"),
        bot_label
    ]

    if worksheet:
        worksheet.append_row(row)
        
        # Логика раскраски
        color_map = {
            "bot1": {"red": 0.9, "green": 0.95, "blue": 1.0},  # Голубой
            "bot2": {"red": 1.0, "green": 0.9, "blue": 0.9},   # Розовый
            "bot3": {"red": 0.9, "green": 1.0, "blue": 0.9},   # Зеленый
        }
        bg_color = color_map.get(bot_label, {"red": 1.0, "green": 1.0, "blue": 1.0})
        
        try:
            last_row = len(worksheet.col_values(1))
            worksheet.format(f"A{last_row}:I{last_row}", {"backgroundColor": bg_color})
        except:
            pass

        return {"status": "success"}
    return {"status": "error"}

router = Router()
@router.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Открыть анкету ОМС", web_app=WebAppInfo(url="https://oms-mini-app-frontend.vercel.app"))
    ]])
    await message.answer("👋 Здравствуйте! Нажмите кнопку, чтобы обновить данные ОМС.", reply_markup=kb)

@app.on_event("startup")
async def startup():
    tokens = get_all_tokens()
    for token in tokens:
        if token:
            bot = Bot(token=token)
            dp = Dispatcher()
            dp.include_router(router)
            asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)






