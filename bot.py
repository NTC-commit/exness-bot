import os
import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiohttp import web

# --- CẤU HÌNH ---
API_TOKEN = "8845615713:AAE1TcY8YlgR6ZA6aBdmiQqDUcivScjFuUY"
ADMIN_IDS = [608027173, 228160692]
RATE_FILE = "rate_usdt.txt"
FEE_FILE = "fee.txt"
BANK_FILE = "banks.txt"
COUNTER_FILE = "counter.txt"
DATE_FILE = "last_date.txt"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- HÀM TIỆN ÍCH ---
def get_val(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return float(f.read().strip())
            except: return default
    return default

def get_next_order_id():
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    last_date = ""
    if os.path.exists(DATE_FILE):
        with open(DATE_FILE, "r") as f: last_date = f.read().strip()
    
    if last_date != today:
        current = 1
        with open(DATE_FILE, "w") as f: f.write(today)
    else:
        current = int(get_val(COUNTER_FILE, 1))
    
    with open(COUNTER_FILE, "w") as f: f.write(str(current + 1))
    return current

def get_bank_info(index):
    if not os.path.exists(BANK_FILE): return None
    with open(BANK_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    try:
        parts = lines[index-1].split('|')
        return {"stk": parts[0], "bank": parts[1], "name": parts[2]}
    except: return None

# --- LỆNH ADMIN ---
@dp.message(Command("setrate"))
async def set_rate(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    with open(RATE_FILE, "w") as f: f.write(m.text.split()[1])
    await m.answer("✅ Đã cập nhật tỷ giá.")

@dp.message(Command("setfee"))
async def set_fee(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    with open(FEE_FILE, "w") as f: f.write(m.text.split()[1].replace('%', ''))
    await m.answer("✅ Đã cập nhật phí.")

@dp.message(Command("addbank"))
async def add_bank(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    with open(BANK_FILE, "a", encoding="utf-8") as f: f.write(m.text.replace("/addbank ", "").strip() + "\n")
    await m.answer("✅ Đã thêm ngân hàng.")

@dp.message(Command("delbank"))
async def del_bank(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    try:
        idx = int(m.text.split()[1]) - 1
        with open(BANK_FILE, "r", encoding="utf-8") as f: lines = f.readlines()
        del lines[idx]
        with open(BANK_FILE, "w", encoding="utf-8") as f: f.writelines(lines)
        await m.answer("✅ Đã xóa.")
    except: await m.answer("⚠️ Lỗi định dạng.")

@dp.message(Command("listbank"))
async def list_bank(m: Message):
    if not os.path.exists(BANK_FILE): 
        await m.answer("Danh sách ngân hàng trống.")
        return
    
    with open(BANK_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    output = "📋 Danh sách ngân hàng:\n\n"
    for i, line in enumerate(lines):
        if not line.strip(): continue
        parts = line.strip().split('|')
        if len(parts) == 3:
            output += (
                f"{i+1}: Bank {i+1}\n"
                f"- 银行名称: {parts[1]}\n"
                f"- 银行账号: {parts[0]}\n"
                f"- 收款人姓名: {parts[2]}\n\n"
            )
    
    await m.answer(output)

# --- XỬ LÝ GIAO DỊCH (TAG BOT) ---
@dp.message()
async def handle_trade(m: Message):
    if not m.text or m.text.startswith("/"): return
    if "@usdt_vpc_bot" not in m.text: return
    
    clean_text = m.text.replace("@usdt_vpc_bot", "").strip()
    args = clean_text.split()
    if len(args) < 2: return
    try:
        amount = float(args[0])
        bank = get_bank_info(int(args[1]))
        if not bank: return await m.answer("⚠️ Không tìm thấy bank.")
        
        rate = get_val(RATE_FILE, 25000)
        fee = get_val(FEE_FILE, 0.6)
        
        real = amount * (1 - fee/100)
        usdt = real / rate
        
        await m.answer(
            f"📅 交易日期: {datetime.now(timezone(timedelta(hours=7))).strftime('%d/%m/%Y')}\n\n"
            f"订单号: #{get_next_order_id()}\n"
            f"收款金额: {amount:,.0f} VNĐ\n"
            f"手续费: {fee}% => 实际到账: {real:,.0f} VNĐ\n"
            f"USDT 汇率: {rate:,.0f}\n"
            f"合作方实收: **{usdt:.2f} USDT**\n\n"
            f"--- 💳 收款信息 ---\n"
            f"银行名称: {bank['bank']}\n"
            f"银行账号: {bank['stk']}\n"
            f"持卡人姓名: {bank['name']}"
        , parse_mode="Markdown")
    except: await m.answer("⚠️ Cú pháp: @usdt_vpc_bot [Số tiền] [Số thứ tự ngân hàng]")

# --- SERVER ---
async def start_web():
    app = web.Application()
    app.add_routes([web.get('/', lambda r: web.Response(text="Bot OK"))])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

async def main():
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
