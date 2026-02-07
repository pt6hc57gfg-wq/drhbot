import os
try:
    import aiocryptopay
except ImportError:
    os.system('pip install aiocryptopay')
    import aiocryptopay
import logging
import asyncio
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from supabase import create_client, Client
from aiocryptopay import AioCryptoPay

# ================== 1. НАСТРОЙКИ ==================
SUPABASE_URL = "https://nlaadpwjsgwurbxtjyim.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sYWFkcHdqc2d3dXJieHRqeWltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzOTYzMTcsImV4cCI6MjA4NTk3MjMxN30.T3h8LomhBI7bjIdXRMQMwUlhVobFQzJhvMlfg_BYFBg"
TOKEN = "8390269866:AAHhAC9qEnUCauTQAVR23f9kHRWxUBwy6Nw"
CP_TOKEN = "526176:AAhBqlDV6Nwz6GP2TzlJtkkkU8kV3A8moLJ" # Вставь токен из @CryptoTestBot или @CryptoBot

ADMIN_ID = 8415442561             
ADMIN_USERNAME = "cemplex"       
GROUP_ID = -1003872240307       
CHAT_LINK = "https://t.me/drhcasino_chat"

FEE = 0.95 # Комиссия 5% (выплата победителю 95%)

# ИЗОБРАЖЕНИЯ
IMG_WALLET = "https://i.postimg.cc/htmRmFP1/IMG_6662.png"
IMG_SUPPORT = "https://i.postimg.cc/VvTM30tg/IMG-6661.png"
IMG_RULES = "https://i.postimg.cc/gcZ5gvby/IMG_6698.jpg"
IMG_PROFILE = "https://i.postimg.cc/m2fyr9zM/IMG-6663.png"
IMG_SUCCESS_PAY = "https://i.postimg.cc/FHXk34V5/IMG-6654.png"

GAMES_EMOJI = {"кубик": "🎲", "дартс": "🎯", "баскет": "🏀", "футбол": "⚽️", "боулинг": "🎳"}

# ================== 2. KEEP-ALIVE (RENDER) ==================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ALIVE")
    def log_message(self, format, *args): return

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# ================== 3. ИНИЦИАЛИЗАЦИЯ И СОСТОЯНИЯ ==================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
crypto = # Найти эту строку:
# crypto = AioCryptoPay(token=CP_TOKEN)

# И заменить на этот блок:
try:
    crypto = AioCryptoPay(token=CP_TOKEN)
    logging.info("CryptoPay initialized successfully")
except Exception as e:
    logging.error(f"КРИТИЧЕСКАЯ ОШИБКА ТОКЕНА CRYPTOPAY: {e}")

class DepositState(StatesGroup):
    waiting_for_amount = State()

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_details = State()

# --- ФУНКЦИИ БАЗЫ ---
def get_user(user_id):
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None
    except: return None

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

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👤 Профиль", "🎮 Список Игр")
    kb.add("👛 Кошелек", "📊 ТОП")
    kb.add("ℹ️ Правила", "🆘 Поддержка")
    kb.add("🚀 Чат проекта")
    return kb

# ================== 4. ОБРАБОТЧИКИ ==================

@dp.message_handler(commands=['start'])
async def cmd_start(m: types.Message):
    register_user(m.from_user.id, m.from_user.first_name)
    txt = "🎲 <b>Добро пожаловать в DRH CASINO!</b>\n\nВыбирай игру в списке, пополняй баланс и побеждай в нашем чате!"
    await m.answer(txt, reply_markup=main_kb())

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0
    txt = (f"<b>🖥️ Профиль игрока</b>\n\n👤 <b>Никнейм:</b> {m.from_user.full_name}\n"
           f"🆔 <b>ID:</b> <code>{m.from_user.id}</code>\n👛 <b>Баланс:</b> <b>{bal} RUB</b>")
    try: await bot.send_photo(m.chat.id, photo=IMG_PROFILE, caption=txt)
    except: await m.answer(txt)

@dp.message_handler(lambda m: m.text == "📊 ТОП")
async def top_players(m: types.Message):
    try:
        res = supabase.table("users").select("name, balance").order("balance", desc=True).limit(15).execute()
        txt = "🏆 <b>ТОП 15 БОГАТЫХ ИГРОКОВ</b>\n\n"
        for i, user in enumerate(res.data, 1):
            prefix = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"<b>{i}.</b>")
            txt += f"{prefix} {user['name']} — <b>{user['balance']}₽</b>\n"
        await m.answer(txt)
    except: await m.answer("Ошибка загрузки топа.")

@dp.message_handler(lambda m: m.text == "🚀 Чат проекта")
async def project_chat_redirect(m: types.Message):
    txt = ("💬 <b>Чат проекта DRH CASINO</b>\n\n🔗 Перейти в чат - @drhcasino_chat\n\n"
           "💎 <b>Именно в этом чате игроки играют между собой в наше казино!</b>")
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➡️ ПЕРЕЙТИ В ЧАТ", url=CHAT_LINK))
    await m.answer(txt, reply_markup=kb)

@dp.message_handler(lambda m: m.text == "👛 Кошелек")
async def wallet(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0
    txt = (f"<b>👛 Кошелек</b>\n\n🪙 <b>Баланс:</b> {bal} RUB\n"
           f"🆔 <b>ID:</b> <code>{m.from_user.id}</code>")
    kb = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton("💎 Пополнить TON", callback_data="dep_ton"),
        types.InlineKeyboardButton("💵 Пополнить USDT", callback_data="dep_usdt"),
        types.InlineKeyboardButton("📤 Вывести RUB", callback_data="withdraw_request")
    )
    try: await bot.send_photo(m.chat.id, photo=IMG_WALLET, caption=txt, reply_markup=kb)
    except: await m.answer(txt, reply_markup=kb)

# --- ЛОГИКА ПОПОЛНЕНИЯ ---
@dp.callback_query_handler(lambda c: c.data.startswith('dep_'))
async def dep_init(c: types.CallbackQuery):
    asset = "TON 💎" if "ton" in c.data else "USDT 💵"
    await c.message.answer(f"<b>⚡️ ПОПОЛНЕНИЕ {asset}</b>\n\nВведите сумму в рублях (мин. 100):")
    await DepositState.waiting_for_amount.set()
    async with dp.current_state(user=c.from_user.id).proxy() as data: data['asset'] = "TON" if "ton" in c.data else "USDT"

@dp.message_handler(state=DepositState.waiting_for_amount)
async def create_inv(m: types.Message, state: FSMContext):
    if not m.text.replace('.','').isdigit(): return await m.answer("Введите число!")
    amount = float(m.text)
    if amount < 100: return await m.answer("Минимум 100 RUB")
    async with state.proxy() as data: asset = data['asset']
    await state.finish()
    inv = await crypto.create_invoice(asset=asset, amount=amount, fiat='RUB', currency_type='fiat')
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 ОПЛАТИТЬ", url=inv.pay_url),
                                          types.InlineKeyboardButton("✅ Я ОПЛАТИЛ!", callback_data=f"check_{inv.invoice_id}"))
    await m.answer(f"🎁 Счёт на {amount} RUB готов!", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_payment(c: types.CallbackQuery):
    inv_id = int(c.data.split('_')[1])
    invs = await crypto.get_invoices(invoice_ids=inv_id)
    inv = invs[0] if isinstance(invs, list) else invs
    if inv.status == 'paid':
        amt = float(inv.amount)
        update_balance(c.from_user.id, amt)
        user_mention = f"@{c.from_user.username}" if c.from_user.username else c.from_user.first_name
        await c.message.edit_text(f"✅ Баланс пополнен на {amt} RUB!")
        chat_txt = (f"<b>✅ Успешное пополнение — {amt} RUB от {user_mention}</b>\n\n"
                    f"🖥️ <b>Игрок ID —</b> <code>{c.from_user.id}</code>")
        try: await bot.send_photo(GROUP_ID, photo=IMG_SUCCESS_PAY, caption=chat_txt)
        except: await bot.send_message(GROUP_ID, chat_txt)
    else: await c.answer("⏳ Оплата не найдена.", show_alert=True)

# --- ЛОГИКА ВЫВОДА ---
@dp.callback_query_handler(lambda c: c.data == "withdraw_request")
async def withdraw_init(c: types.CallbackQuery):
    u = get_user(c.from_user.id)
    if not u or u['balance'] < 100:
        return await c.answer("❌ Минимальная сумма для вывода: 100 RUB", show_alert=True)
    await c.message.answer("💸 <b>Введите сумму для вывода:</b>\n<i>Минимум 100 RUB</i>")
    await WithdrawState.waiting_for_amount.set()

@dp.message_handler(state=WithdrawState.waiting_for_amount)
async def withdraw_amount(m: types.Message, state: FSMContext):
    if not m.text.replace('.','').isdigit(): return await m.answer("Введите число.")
    amount = float(m.text)
    u = get_user(m.from_user.id)
    if amount < 100: return await m.answer("❌ Минимальная сумма — 100 RUB.")
    if amount > u['balance']: return await m.answer(f"❌ Недостаточно средств! Баланс: {u['balance']}₽")
    await state.update_data(withdraw_amount=amount)
    await m.answer("📝 <b>Введите ваш @Юзернейм или ID</b>\n\n💡 <i>Администратор отправит вам чек CryptoBot на указанный контакт.</i>")
    await WithdrawState.waiting_for_details.set()

@dp.message_handler(state=WithdrawState.waiting_for_details)
async def withdraw_final(m: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data['withdraw_amount']
    details = m.text
    await state.finish()
    update_balance(m.from_user.id, -amount) # Списание сразу
    await m.answer(f"✅ <b>Заявка создана!</b>\nСумма: {amount}₽\nОжидайте выплату в ЛС.")
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Отклонить и вернуть 💰", callback_data=f"reject_{m.from_user.id}_{amount}"))
    admin_msg = (f"📩 <b>ЗАЯВКА НА ВЫВОД</b>\n\n👤 <b>Игрок:</b> {m.from_user.mention}\n"
                 f"💰 <b>Сумма:</b> {amount} RUB\n🔗 <b>Куда слать:</b> <code>{details}</code>")
    await bot.send_message(ADMIN_ID, admin_msg, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('reject_'))
async def reject_withdraw(c: types.CallbackQuery):
    _, user_id, amount = c.data.split('_')
    update_balance(int(user_id), float(amount))
    try: await bot.send_message(int(user_id), f"❌ Ваша заявка на {amount}₽ отклонена. Деньги вернулись на баланс.")
    except: pass
    await c.message.edit_text(c.message.text + "\n\n🔴 <b>ОТКЛОНЕНО. Баланс игрока восстановлен.</b>")

# --- ИГРОВАЯ ЛОГИКА ---
@dp.message_handler(lambda m: m.text == "ℹ️ Правила")
async def rules(m: types.Message):
    txt = "ℹ️ <b>ПРАВИЛА КАЗИНО DRH</b>\n\n1. Игры в чате.\n2. Комиссия 5%.\n3. Выплаты чеками."
    try: await bot.send_photo(m.chat.id, photo=IMG_RULES, caption=txt)
    except: await m.answer(txt)

@dp.message_handler(lambda m: m.text == "🎮 Список Игр")
async def g_list(m: types.Message):
    await m.answer("🎰 <b>Игры:</b> Кубик, Дартс, Баскет, Футбол, Боулинг\nКоманда: <code>/game 100 футбол</code>")

@dp.message_handler(commands=['game'])
async def play_game(m: types.Message):
    if m.chat.id == m.from_user.id: return
    args = m.get_args().split()
    if not args: return
    try:
        bet = float(args[0])
        g_type = args[1].lower() if len(args) > 1 else "кубик"
        u = get_user(m.from_user.id)
        if not u or u['balance'] < bet: return await m.answer("❌ Нет денег!")
        emoji = GAMES_EMOJI.get(g_type, "🎲")
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"Принять {bet}₽ {emoji}", callback_data=f"j_{m.from_user.id}_{bet}_{g_type}"))
        await m.answer(f"🎮 <b>БИТВА: {g_type.upper()}</b>\n👤 {m.from_user.mention} ставит {bet}₽", reply_markup=kb)
    except: pass

@dp.callback_query_handler(lambda c: c.data.startswith('j_'))
async def join_game(c: types.CallbackQuery):
    _, cr_id, bet, g_type = c.data.split('_')
    cr_id, bet, jo_id = int(cr_id), float(bet), c.from_user.id
    if jo_id == cr_id: return
    cr_u, jo_u = get_user(cr_id), get_user(jo_id)
    if not cr_u or cr_u['balance'] < bet or not jo_u or jo_u['balance'] < bet: return
    update_balance(cr_id, -bet); update_balance(jo_id, -bet)
    emoji = GAMES_EMOJI.get(g_type, "🎲")
    await c.message.edit_text(f"🎲 <b>ИГРА: {g_type.upper()}</b>")
    m1 = await bot.send_dice(c.message.chat.id, emoji=emoji); v1 = m1.dice.value
    await asyncio.sleep(4); m2 = await bot.send_dice(c.message.chat.id, emoji=emoji); v2 = m2.dice.value
    win = round((bet * 2) * FEE, 2)
    if v1 > v2: update_balance(cr_id, win); res = f"🏆 {cr_u['name']} победил! (+{win}₽)"
    elif v2 > v1: update_balance(jo_id, win); res = f"🏆 {jo_u['name']} победил! (+{win}₽)"
    else: update_balance(cr_id, bet); update_balance(jo_id, bet); res = "Ничья! Возврат."
    await bot.send_message(c.message.chat.id, res)

@dp.message_handler(lambda m: m.text == "🆘 Поддержка")
async def supp(m: types.Message):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👨‍💻 Админ", url=f"https://t.me/{ADMIN_USERNAME}"))
    try: await bot.send_photo(m.chat.id, photo=IMG_SUPPORT, caption=f"🆘 Поддержка: @{ADMIN_USERNAME}", reply_markup=kb)
    except: await m.answer(f"🆘 Поддержка: @{ADMIN_USERNAME}", reply_markup=kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
