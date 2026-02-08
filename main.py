import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from supabase import create_client, Client

# ================== 1. НАСТРОЙКИ ==================
SUPABASE_URL = "https://nlaadpwjsgwurbxtjyim.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sYWFkcHdqc2d3dXJieHRqeWltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzOTYzMTcsImV4cCI6MjA4NTk3MjMxN30.T3h8LomhBI7bjIdXRMQMwUlhVobFQzJhvMlfg_BYFBg"

TOKEN = "8390269866:AAHhAC9qEnUCauTQAVR23f9kHRWxUBwy6Nw"
ADMIN_ID = 8415442561  # Твой ID для проверки чеков         
GROUP_ID = -1003872240307 # ID чата для уведомлений      
CHAT_LINK = "https://t.me/drhcasino_chat"
ADMIN_USERNAME = "cemplex" 

# Твои реквизиты
CARD_REQUISITES = "2200700764562608"

# КАРТИНКИ (Добавлены все ссылки)
IMG_WALLET = "https://i.postimg.cc/htmRmFP1/IMG_6662.png"
IMG_PROFILE = "https://i.postimg.cc/VvTM30tg/IMG_6661.png"
IMG_SUPPORT = "https://i.postimg.cc/VvTM30tg/IMG-6661.png"
IMG_RULES = "https://i.postimg.cc/gcZ5gvby/IMG_6698.jpg"
IMG_SUCCESS_PAY = "https://i.postimg.cc/FHXk34V5/IMG-6654.png" # КАРТИНКА ДЛЯ ЧАТА ПРИ ПОПОЛНЕНИИ

GAMES_EMOJI = {"кубик": "🎲", "дартс": "🎯", "баскет": "🏀", "футбол": "⚽️", "боулинг": "🎳"}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class DepositState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_check = State()

# ================== 2. БАЗА ДАННЫХ ==================
def get_user(user_id):
    res = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

def update_balance(user_id, amount):
    u = get_user(user_id)
    if u:
        new_bal = round(float(u['balance']) + amount, 2)
        supabase.table("users").update({"balance": new_bal}).eq("user_id", user_id).execute()
        return new_bal
    return 0

def get_game_number():
    try:
        res = supabase.table("stats").select("value").eq("name", "games_count").execute()
        val = res.data[0]['value'] + 1 if res.data else 1
        supabase.table("stats").upsert({"name": "games_count", "value": val}).execute()
        return val
    except: return 0

# ================== 3. ОБРАБОТЧИКИ МЕНЮ ==================

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(m: types.Message, state: FSMContext):
    await state.finish()
    if not get_user(m.from_user.id):
        supabase.table("users").insert({"user_id": m.from_user.id, "name": m.from_user.first_name, "balance": 0.0}).execute()
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👤 Профиль", "🎮 Список Игр", "👛 Кошелек", "📊 ТОП", "ℹ️ Правила", "🆘 Поддержка", "🚀 Чат проекта")
    await m.answer("🎲 <b>Добро пожаловать в DRH CASINO!</b>", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "👤 Профиль", state="*")
async def profile(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0.0
    await bot.send_photo(m.chat.id, photo=IMG_PROFILE, caption=f"<b>🖥️ ПРОФИЛЬ</b>\n\n🆔 ID: <code>{m.from_user.id}</code>\n👛 Баланс: <b>{bal} RUB</b>")

@dp.message_handler(lambda m: m.text == "👛 Кошелек", state="*")
async def wallet(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0.0
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➕ Пополнить баланс", callback_data="sbp_dep"))
    await bot.send_photo(m.chat.id, photo=IMG_WALLET, caption=f"<b>👛 КОШЕЛЕК</b>\n\n🪙 Баланс: <b>{bal} RUB</b>", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🆘 Поддержка", state="*")
async def support(m: types.Message):
    await bot.send_photo(m.chat.id, photo=IMG_SUPPORT, caption=f"🆘 <b>Техническая поддержка</b>\n\nПишите администратору: @{ADMIN_USERNAME}")

@dp.message_handler(lambda m: m.text == "ℹ️ Правила", state="*")
async def rules(m: types.Message):
    text = "ℹ️ <b>Правила DRH CASINO</b>\n\n1. Минимум пополнения — 100 RUB.\n2. Комиссия — 5%.\n3. При пополнении ОБЯЗАТЕЛЬНО скриншот чека!"
    await bot.send_photo(m.chat.id, photo=IMG_RULES, caption=text)

# ================== 4. ПОПОЛНЕНИЕ (СБП) ==================

@dp.callback_query_handler(lambda c: c.data == "sbp_dep", state="*")
async def sbp_dep(c: types.CallbackQuery):
    await c.message.answer("💰 <b>Введите сумму пополнения в RUB:</b>")
    await DepositState.waiting_for_amount.set()
    await c.answer()

@dp.message_handler(state=DepositState.waiting_for_amount)
async def sbp_amount(m: types.Message, state: FSMContext):
    try:
        amount = float(m.text.replace(',', '.'))
        await state.update_data(amount=amount)
        text = (
            f"🏆 <b>Пополнение баланса:</b>\n\n"
            f"ℹ️ Чтобы пополнить баланс пожалуйста скиньте желаемую сумму на реквизиты и <b>ОБЯЗАТЕЛЬНО</b> отправьте скриншот (не файл) чек оплаты!\n\n"
            f"🎯 Реквизиты - <code>{CARD_REQUISITES}</code>\n\n"
            f"⁉️ Ожидайте, баланс пополнится после проверки!"
        )
        await m.answer(text)
        await DepositState.waiting_for_check.set()
    except: await m.answer("❌ Введите сумму числом.")

@dp.message_handler(content_types=['photo'], state=DepositState.waiting_for_check)
async def sbp_check(m: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get('amount', 0)
    await state.finish()
    await m.answer("⏳ <b>Скриншот отправлен на проверку!</b>")
    
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(f"✅ Одобрить {amount}₽", callback_data=f"adm_ok_{m.from_user.id}_{amount}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no_{m.from_user.id}")
    )
    await bot.send_photo(ADMIN_ID, photo=m.photo[-1].file_id, 
                         caption=f"🔔 <b>ЧЕК:</b> {m.from_user.mention}\nСумма: {amount} RUB", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('adm_'))
async def admin_decision(c: types.CallbackQuery):
    data = c.data.split('_')
    action, user_id = data[1], int(data[2])
    
    if action == 'ok':
        amount = float(data[3])
        update_balance(user_id, amount)
        user = get_user(user_id)
        # 1. Сообщение пользователю
        await bot.send_message(user_id, f"✅ <b>Зачислено: {amount} RUB</b>")
        # 2. Сообщение в общий чат с картинкой
        try:
            chat_text = f"💰 <b>НОВОЕ ПОПОЛНЕНИЕ!</b>\n\n👤 Игрок: {user['name']}\n💵 Сумма: <b>{amount} RUB</b>\n\nЖелаем удачных игр в DRH CASINO! 🎲"
            await bot.send_photo(GROUP_ID, photo=IMG_SUCCESS_PAY, caption=chat_text)
        except Exception as e: logging.error(f"Chat notify error: {e}")
        
        await c.message.edit_caption(f"✅ ОДОБРЕНО для {user_id}")
    else:
        await bot.send_message(user_id, "❌ <b>Чек отклонен администратором.</b>")
        await c.message.edit_caption(f"❌ ОТКЛОНЕНО для {user_id}")
    await c.answer()

# ================== 5. ИГРЫ И ЧАТ ==================

@dp.message_handler(commands=['бал', 'b', 'bal'], state="*")
@dp.message_handler(lambda m: m.text and m.text.lower() in ['бал', 'b', 'bal'], state="*")
async def chat_bal(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0.0
    await m.reply(f"💰 Ваш баланс: <b>{bal} RUB</b>")

@dp.message_handler(commands=['game'], state="*")
async def start_game(m: types.Message):
    if m.chat.id == m.from_user.id: return 
    args = m.get_args().split()
    if len(args) < 2: return await m.answer("Пример: <code>/game 100 кубик</code>")
    try: bet = float(args[0]); g_type = args[1].lower()
    except: return
    if g_type not in GAMES_EMOJI: return
    u = get_user(m.from_user.id)
    if not u or u['balance'] < bet: return await m.answer("❌ Недостаточно средств")
    
    emoji = GAMES_EMOJI[g_type]
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"Принять {bet}₽ {emoji}", callback_data=f"j_{m.from_user.id}_{bet}_{g_type}"))
    await m.answer(f"🎮 <b>БИТВА</b>\n👤 {m.from_user.mention} ставит <b>{bet}₽</b>", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('j_'), state="*")
async def join_game(c: types.CallbackQuery):
    _, cr_id, bet, g_type = c.data.split('_')
    cr_id, bet, jo_id = int(cr_id), float(bet), c.from_user.id
    if jo_id == cr_id: return await c.answer("Нельзя с собой!", show_alert=True)
    cr_u, jo_u = get_user(cr_id), get_user(jo_id)
    if not jo_u or jo_u['balance'] < bet: return await c.answer("❌ Нет денег!", show_alert=True)
    
    update_balance(cr_id, -bet); update_balance(jo_id, -bet)
    emoji = GAMES_EMOJI[g_type]
    await c.message.edit_text(f"🎲 <b>ИГРА: {g_type.upper()}</b>")
    
    m1 = await bot.send_dice(c.message.chat.id, emoji=emoji); v1 = m1.dice.value
    await asyncio.sleep(4)
    m2 = await bot.send_dice(c.message.chat.id, emoji=emoji); v2 = m2.dice.value
    
    win_sum = round((bet * 2) * 0.95, 2)
    game_num = get_game_number()
    winner = None
    if v1 > v2: update_balance(cr_id, win_sum); winner = cr_u
    elif v2 > v1: update_balance(jo_id, win_sum); winner = jo_u
    else: update_balance(cr_id, bet); update_balance(jo_id, bet)

    res_text = (
        f"<b>{g_type.capitalize()} {emoji} №{game_num}</b>\n\n"
        f"📎 <a href='https://t.me/drhcasino_chat'>Наш чат</a>\n\n"
        f"💰 Выигрыш: <b>{win_sum if winner else '0'} RUB</b>\n\n"
        f"👥 Игроки:\n"
        f"1️⃣ - {cr_u['name']}\n"
        f"2️⃣ - {jo_u['name']}\n\n"
        f"⚡️ Победитель: {winner['name'] if winner else 'Ничья (возврат)'}"
    )
    await bot.send_message(c.message.chat.id, res_text, disable_web_page_preview=True)

@dp.message_handler(lambda m: m.text == "🚀 Чат проекта", state="*")
async def project_chat(m: types.Message):
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➡️ В ЧАТ", url=CHAT_LINK))
    await bot.send_message(m.chat.id, "Заходи в чат и играй!", reply_markup=kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
