import logging
import asyncio
import threading
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- АВТО-УСТАНОВКА БИБЛИОТЕК ---
try:
    from aiogram import Bot, Dispatcher, types, executor
    from aiogram.contrib.fsm_storage.memory import MemoryStorage
    from aiogram.dispatcher import FSMContext
    from aiogram.dispatcher.filters.state import State, StatesGroup
    from supabase import create_client, Client
    from aiocryptopay import AioCryptoPay
except ImportError:
    os.system('pip install aiogram==2.25.1 supabase aiocryptopay httpx')
    os.execv(sys.executable, ['python'] + sys.argv)

# ================== 1. НАСТРОЙКИ ==================
SUPABASE_URL = "https://nlaadpwjsgwurbxtjyim.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sYWFkcHdqc2d3dXJieHRqeWltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzOTYzMTcsImV4cCI6MjA4NTk3MjMxN30.T3h8LomhBI7bjIdXRMQMwUlhVobFQzJhvMlfg_BYFBg"

TOKEN = "8390269866:AAHhAC9qEnUCauTQAVR23f9kHRWxUBwy6Nw"
CP_TOKEN = "526176:AAK1hOScJeeHYEnvAvgYhMNkNL1KZfN6ps7" # Замени на свой токен

ADMIN_ID = 8415442561             
ADMIN_USERNAME = "cemplex"       
GROUP_ID = -1003872240307       
CHAT_LINK = "https://t.me/drhcasino_chat"
FEE = 0.95 # Комиссия (5%)

# ИЗОБРАЖЕНИЯ
IMG_WALLET = "https://i.postimg.cc/htmRmFP1/IMG_6662.png"
IMG_SUPPORT = "https://i.postimg.cc/VvTM30tg/IMG-6661.png"
IMG_RULES = "https://i.postimg.cc/gcZ5gvby/IMG_6698.jpg"
IMG_PROFILE = "https://i.postimg.cc/m2fyr9zM/IMG-6663.png"
IMG_SUCCESS_PAY = "https://i.postimg.cc/FHXk34V5/IMG-6654.png"

GAMES_EMOJI = {"кубик": "🎲", "дартс": "🎯", "баскет": "🏀", "футбол": "⚽️", "боулинг": "🎳"}

# ================== 2. KEEP-ALIVE ==================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args): return

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# ================== 3. ИНИЦИАЛИЗАЦИЯ ==================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
crypto = AioCryptoPay(token=CP_TOKEN)

class DepositState(StatesGroup):
    waiting_for_amount = State()

# --- ФУНКЦИИ БАЗЫ ---
def get_user(user_id):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

def register_user(user_id, name):
    if not get_user(user_id):
        supabase.table("users").insert({"user_id": user_id, "name": name, "balance": 0.0}).execute()

def update_balance(user_id, amount):
    user = get_user(user_id)
    if user:
        new_bal = round(user['balance'] + amount, 2)
        supabase.table("users").update({"balance": new_bal}).eq("user_id", user_id).execute()
        return new_bal
    return 0

def get_game_number():
    # Простейший счетчик игр через БД Supabase
    try:
        res = supabase.table("stats").select("value").eq("name", "games_count").execute()
        if not res.data:
            supabase.table("stats").insert({"name": "games_count", "value": 1}).execute()
            return 1
        new_val = res.data[0]['value'] + 1
        supabase.table("stats").update({"value": new_val}).eq("name", "games_count").execute()
        return new_val
    except: return 0

async def send_safely(chat_id, photo_url, caption, reply_markup=None):
    try: await bot.send_photo(chat_id, photo=photo_url, caption=caption, reply_markup=reply_markup)
    except: await bot.send_message(chat_id, text=caption, reply_markup=reply_markup)

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👤 Профиль", "🎮 Список Игр", "👛 Кошелек", "📊 ТОП", "ℹ️ Правила", "🆘 Поддержка", "🚀 Чат проекта")
    return kb

# ================== 4. ОБРАБОТЧИКИ ==================

# --- КОМАНДЫ БАЛАНСА ---
@dp.message_handler(commands=['бал', 'b', 'bal'])
@dp.message_handler(lambda m: m.text and m.text.lower() in ['бал', 'b', 'bal'])
async def check_bal_cmd(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0.0
    await m.reply(f"💰 Ваш баланс: <b>{bal} RUB</b>")

@dp.message_handler(commands=['start'])
async def cmd_start(m: types.Message):
    register_user(m.from_user.id, m.from_user.first_name)
    await m.answer("🎲 <b>Добро пожаловать в DRH CASINO!</b>", reply_markup=main_kb())

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0
    txt = f"<b>🖥️ Профиль</b>\n\n👤 Ник: {m.from_user.full_name}\n👛 Баланс: <b>{bal} RUB</b>"
    await send_safely(m.chat.id, IMG_PROFILE, txt)

@dp.message_handler(lambda m: m.text == "👛 Кошелек")
async def wallet(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0
    txt = f"<b>👛 Кошелек</b>\n\n🪙 Баланс: {bal} RUB"
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➕ Пополнить", callback_data="dep_init"))
    await send_safely(m.chat.id, IMG_WALLET, txt, kb)

# --- ПОПОЛНЕНИЕ ---
@dp.callback_query_handler(lambda c: c.data == 'dep_init')
async def dep_start(c: types.CallbackQuery):
    await c.message.answer("💳 <b>Введите сумму в RUB (мин. 100):</b>")
    await DepositState.waiting_for_amount.set()

@dp.message_handler(state=DepositState.waiting_for_amount)
async def create_inv(m: types.Message, state: FSMContext):
    try:
        amount = float(m.text.replace(',', '.'))
        if amount < 100: raise ValueError
    except: return await m.answer("❌ Минимум 100 RUB")
    
    await state.finish()
    try:
        inv = await crypto.create_invoice(asset='TON', amount=amount, fiat='RUB', currency_type='fiat')
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 ОПЛАТИТЬ", url=inv.pay_url),
                                              types.InlineKeyboardButton("✅ ПРОВЕРИТЬ", callback_data=f"check_{inv.invoice_id}"))
        await m.answer(f"💎 Счет на {amount}₽ создан!", reply_markup=kb)
    except Exception as e: await m.answer(f"❌ Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_pay(c: types.CallbackQuery):
    inv_id = int(c.data.split('_')[1])
    inv = (await crypto.get_invoices(invoice_ids=inv_id))[0]
    if inv.status == 'paid':
        sum_add = float(inv.fiat_amount or inv.amount)
        update_balance(c.from_user.id, sum_add)
        await c.message.edit_text(f"✅ Зачислено {sum_add} RUB!")
        try:
            chat_txt = f"💰 <b>НОВОЕ ПОПОЛНЕНИЕ!</b>\n\n👤 Игрок: {c.from_user.mention}\n💵 Сумма: <b>{sum_add} RUB</b>"
            await bot.send_photo(GROUP_ID, photo=IMG_SUCCESS_PAY, caption=chat_txt)
        except: pass
    else: await c.answer("⏳ Оплата не найдена", show_alert=True)

# --- ИГРОВАЯ ЛОГИКА ---
@dp.message_handler(commands=['game'])
async def play_game(m: types.Message):
    if m.chat.id == m.from_user.id: return # Только в чатах
    args = m.get_args().split()
    if len(args) < 2: return await m.answer("Пример: <code>/game 100 кубик</code>")
    
    try: bet = float(args[0])
    except: return
    
    g_type = args[1].lower()
    if g_type not in GAMES_EMOJI: return await m.answer("Доступны: кубик, дартс, баскет, футбол, боулинг")
    
    u = get_user(m.from_user.id)
    if not u or u['balance'] < bet: return await m.answer("❌ Недостаточно средств!")
    
    emoji = GAMES_EMOJI[g_type]
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"Принять {bet}₽ {emoji}", callback_data=f"j_{m.from_user.id}_{bet}_{g_type}"))
    await m.answer(f"🎮 <b>БИТВА</b>\n👤 {m.from_user.mention} ставит <b>{bet}₽</b>", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('j_'))
async def join_game(c: types.CallbackQuery):
    _, cr_id, bet, g_type = c.data.split('_')
    cr_id, bet, jo_id = int(cr_id), float(bet), c.from_user.id
    if jo_id == cr_id: return await c.answer("Нельзя играть с самим собой!", show_alert=True)
    
    cr_u, jo_u = get_user(cr_id), get_user(jo_id)
    if not jo_u or jo_u['balance'] < bet: return await c.answer("❌ У вас нет денег!", show_alert=True)
    if cr_u['balance'] < bet: return await c.message.edit_text("❌ У создателя кончились деньги.")

    update_balance(cr_id, -bet); update_balance(jo_id, -bet)
    emoji = GAMES_EMOJI[g_type]
    
    await c.message.edit_text(f"🎲 <b>ИГРА НАЧАЛАСЬ: {g_type.upper()}</b>")
    
    m1 = await bot.send_dice(c.message.chat.id, emoji=emoji); v1 = m1.dice.value
    await asyncio.sleep(4)
    m2 = await bot.send_dice(c.message.chat.id, emoji=emoji); v2 = m2.dice.value
    await asyncio.sleep(1)
    
    win_sum = round((bet * 2) * FEE, 2)
    game_num = get_game_number()
    
    winner = None
    if v1 > v2:
        update_balance(cr_id, win_sum); winner = cr_u
    elif v2 > v1:
        update_balance(jo_id, win_sum); winner = jo_u
    else:
        update_balance(cr_id, bet); update_balance(jo_id, bet)

    # ФОРМИРУЕМ ФИНАЛЬНЫЙ ТЕКСТ ПО ТВОЕМУ ЗАПРОСУ
    result_text = (
        f"{g_type.capitalize()} {emoji} №{game_num}\n\n"
        f"📎 <a href='{CHAT_LINK}'>Наш чат</a>\n\n"
        f"💰 Выигрыш: <b>{win_sum if winner else '0'} RUB</b>\n\n"
        f"👥 Игроки:\n"
        f"1️⃣ - {cr_u['name']}\n"
        f"2️⃣ - {jo_u['name']}\n\n"
        f"⚡️ Победитель: {winner['name'] if winner else 'Ничья (возврат)'}"
    )
    
    await bot.send_message(c.message.chat.id, result_text, disable_web_page_preview=True)

# --- ПРОЧЕЕ ---
@dp.message_handler(lambda m: m.text == "🚀 Чат проекта")
async def project_chat(m: types.Message):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➡️ В ЧАТ", url=CHAT_LINK))
    await m.answer("💬 Заходи в наш игровой чат!", reply_markup=kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
