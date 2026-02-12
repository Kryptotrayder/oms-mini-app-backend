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
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Google Sheets Setup
worksheet = None
try:
    creds_json = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    gc = authorize(creds)
    spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1W6nk5COB4vLQFPzK4upA6wuGT7Q0_3NRYMjEdTxHxZQ/edit")
    worksheet = spreadsheet.sheet1
except Exception as e:
    print(f"Sheets Error: {e}")

def validate_tg_data(init_data_raw: str):
    if not init_data_raw:
        return None
    try:
        parsed = urllib.parse.parse_qs(init_data_raw)
        received_hash = parsed.pop("hash", [None])[0]
        data_check_string = "\n".join([f"{k}={v[0]}" for k, v in sorted(parsed.items())])
        
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calc_hash == received_hash:
            user_data = json.loads(parsed.get("user", ["{}"])[0])
            return user_data
    except:
        pass
    return None

@app.post("/submit")
async def submit(request: Request):
    data = await request.json()
    init_raw = data.get("initDataRaw")
    
    # Пытаемся получить реального юзера
    user = validate_tg_data(init_raw)
    user_id = str(user.get("id")) if user else "Unknown"
    username = user.get("username", "Unknown") if user else "Unknown"

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_id,
        username,
        data.get("gender"),
        data.get("name"),
        data.get("polis"),
        f"{data.get('docType')} {data.get('docNumber')}",
        data.get("phone")
    ]

    if worksheet:
        worksheet.append_row(row)
        return {"status": "ok"}
    raise HTTPException(status_code=500, detail="Sheet not connected")

# Bot Logic
router = Router()
@router.message(Command("start"))
async def cmd_start(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть ОМС", web_app=WebAppInfo(url="https://oms-mini-app-frontend.vercel.app"))
    ]])
    await m.answer("Нажмите кнопку ниже:", reply_markup=kb)

@app.on_event("startup")
async def on_startup():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



