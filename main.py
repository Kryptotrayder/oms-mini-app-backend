import os
import json
import asyncio
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
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

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_all_tokens():
    tokens = [v for k, v in os.environ.items() if k.startswith("BOT_TOKEN")]
    if not tokens:
        single_token = os.getenv("BOT_TOKEN")
        if single_token:
            tokens.append(single_token)
    return tokens

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

# --- ГУГЛ ТАБЛИЦЫ ---

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

# --- ОБРАБОТЧИКИ API ---

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
    bot_label = data.get("bot_label", "bot1")
    if bot_label == "unknown" or not bot_label:
        bot_label = "bot1"

    user = get_telegram_user(init_raw)
    user_id = str(user.get("id", "Unknown")) if user else "Unknown"
    username = user.get("username", "Unknown") if user else "Unknown"

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
        try:
            res = worksheet.append_row(row, value_input_option='RAW')
            
            color_map = {
                "bot1": {"red": 0.8, "green": 0.9, "blue": 1.0},
                "bot2": {"red": 1.0, "green": 0.85, "blue": 0.85},
                "bot3": {"red": 0.85, "green": 1.0, "blue": 0.85},
            }
            bg_color = color_map.get(bot_label, {"red": 0.95, "green": 0.95, "blue": 0.95})
            
            updated_range = res.get('updates').get('updatedRange')
            row_idx = updated_range.split('!A')[1].split(':')[0]
            
            worksheet.format(f"A{row_idx}:I{row_idx}", {"backgroundColor": bg_color})
            return {"status": "success"}
        except Exception as e:
            print(f"❌ Ошибка записи: {e}")
            return {"status": "error"}
    return {"status": "error"}

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

async def start_handler(message: Message):
    # Используем одинарные кавычки внутри двойных, чтобы не было ошибки
    await message.answer("👋 Здравствуйте! Пожалуйста, воспользуйтесь синей кнопкой 'Начать' для обновления данных ОМС.")

@app.on_event("startup")
async def startup():
    tokens = get_all_tokens()
    print(f"🤖 Найдено ботов для запуска: {len(tokens)}")
    for token in tokens:
        if not token: continue
        try:
            bot = Bot(token=token)
            dp = Dispatcher()
            dp.message.register(start_handler, Command("start"))
            asyncio.create_task(dp.start_polling(bot))
            print(f"✅ Бот запущен: {token[:8]}...")
        except Exception as e:
            print(f"❌ Ошибка запуска бота: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




