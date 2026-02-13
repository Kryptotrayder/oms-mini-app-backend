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
        if single_token: tokens.append(single_token)
    return tokens

def get_telegram_user(init_data_raw: str):
    if not init_data_raw: return None
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_raw))
        if "user" in parsed_data: return json.loads(parsed_data["user"])
    except: pass
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

# --- ЛОГИКА НАПОМИНАНИЙ ---

async def check_and_remind(user_id, bot_label, delay_sec):
    """Ждет указанное время и шлет сообщение, если ID не появился в таблице"""
    await asyncio.sleep(delay_sec)
    
    try:
        if worksheet:
            # Проверяем 2-й столбец (ID пользователей)
            existing_ids = worksheet.col_values(2)
            if str(user_id) not in existing_ids:
                tokens = get_all_tokens()
                # Выбираем токен: bot1 -> 0, bot2 -> 1
                idx = 1 if bot_label == "bot2" else 0
                if idx < len(tokens):
                    bot = Bot(token=tokens[idx])
                    await bot.send_message(
                        user_id, 
                        "Вы не закончили регистрацию, нажмите на синюю кнопку 'Начать', чтобы заново или продолжить регистрацию."
                    )
                    await bot.session.close()
    except Exception as e:
        print(f"Ошибка в напоминании: {e}")

@app.post("/set_reminder")
async def set_reminder(request: Request):
    data = await request.json()
    user = get_telegram_user(data.get("initDataRaw", ""))
    bot_label = data.get("bot_label", "bot1")
    
    if user:
        u_id = user.get("id")
        # Запускаем две независимые задачи (через 10 и 20 мин)
        asyncio.create_task(check_and_remind(u_id, bot_label, 600))  # 10 мин
        asyncio.create_task(check_and_remind(u_id, bot_label, 1200)) # 20 мин
        
    return {"status": "reminders_set"}

# --- ОБРАБОТЧИКИ API ---

@app.post("/check_user")
async def check_user(request: Request):
    data = await request.json()
    user = get_telegram_user(data.get("initDataRaw", ""))
    if not user or not worksheet: return {"is_blocked": False}
    try:
        if str(user.get("id")) in worksheet.col_values(2): return {"is_blocked": True}
    except: pass
    return {"is_blocked": False}

@app.post("/submit")
async def submit(request: Request):
    data = await request.json()
    bot_label = data.get("bot_label", "bot1")
    user = get_telegram_user(data.get("initDataRaw", ""))
    if not user: return {"status": "error"}

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        str(user.get("id")),
        user.get("username", "Unknown"),
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
            }
            bg_color = color_map.get(bot_label, {"red": 1.0, "green": 1.0, "blue": 1.0})
            row_idx = res.get('updates').get('updatedRange').split('!A')[1].split(':')[0]
            worksheet.format(f"A{row_idx}:I{row_idx}", {"backgroundColor": bg_color})
            return {"status": "success"}
        except: return {"status": "error"}
    return {"status": "error"}

# --- ТЕЛЕГРАМ ---

async def start_handler(message: Message):
    await message.answer("👋 Здравствуйте! Пожалуйста, воспользуйтесь синей кнопкой 'Начать' для обновления данных ОМС.")

@app.on_event("startup")
async def startup():
    tokens = get_all_tokens()
    for token in tokens:
        if not token: continue
        bot = Bot(token=token)
        dp = Dispatcher()
        dp.message.register(start_handler, Command("start"))
        asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



