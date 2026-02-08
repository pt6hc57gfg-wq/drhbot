import threading
from flask import Flask

# Создаем маленькое приложение Flask
app = Flask('')

@app.route('/')
def home():
    return "Бот запущен!"

def run_web():
    # Render прокидывает порт в переменную окружения PORT
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Запускаем сервер в фоновом потоке
threading.Thread(target=run_web).start()
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from supabase import create_client, Client

# ================== 1. НАСТРОЙКИ ==================
SUPABASE_URL = "https://nlaadpwjsgwurbxtjyim.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sYWFkcHdqc2d3dXJieHRqeWltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzOTYzMTcsImV4cCI6MjA4NTk3MjMxN30.T3h8LomhBI7bjIdXRMQMwUlhVobFQzJhvMlfg_BYFBg"

# ВСТАВЬ СВОЙ НОВЫЙ ТОКЕН ТУТ:
TOKEN = "8390269866:AAGAd9x0maUU-eIpODOrw-yAkFi73rFJ73k" 

ADMIN_ID = 8415442561             
GROUP_ID = -1003872240307       
CHAT_LINK = "https://t.me/drhcasino_chat"
ADMIN_USERNAME = "cemplex" 
CARD_REQUISITES = "2200700764562608"

# КАРТИНКИ
IMG_WALLET = "https://i.postimg.cc/htmRmFP1/IMG_6662.png"
IMG_PROFILE = "https://i.postimg.cc/VvTM30tg/IMG_6661.png"
IMG_SUPPORT = "https://i.postimg.cc/VvTM30tg/IMG_6661.png"
IMG_RULES = "https://i.postimg.cc/gcZ5gvby/IMG_6698.jpg"
IMG_SUCCESS_PAY = "https://i.postimg.cc/FHXk34V5/IMG-6654.png"

GAMES_EMOJI = {"кубик": "🎲", "дартс": "🎯", "баскет": "🏀", "футбол": "⚽️", "боулинг": "🎳"}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# СОСТОЯНИЯ (FSM)
class DepositState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_check = State()

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_details = State()

class TransferState(StatesGroup):
    waiting_for_username = State()
    waiting_for_amount = State()

# ================== 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def get_user(user_id):
    try:
        res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None
    except: return None

def get_user_by_username(username):
    username = username.replace("@", "").lower()
    try:
        res = supabase.table("users").select("*").ilike("username", username).execute()
        return res.data[0] if res.data else None
    except: return None

def update_balance(user_id, amount):
    u = get_user(user_id)
    if u:
        new_bal = round(float(u['balance']) + amount, 2)
        supabase.table("users").update({"balance": new_bal}).eq("user_id", user_id).execute()
        return new_bal
    return 0

def add_stat(user_id, stat_type):
    u = get_user(user_id)
    if u:
        current_val = u.get(stat_type, 0)
        supabase.table("users").update({stat_type: current_val + 1}).eq("user_id", user_id).execute()

def get_game_number():
    try:
        res = supabase.table("stats").select("value").eq("name", "games_count").execute()
        val = res.data[0]['value'] + 1 if res.data else 1
        supabase.table("stats").upsert({"name": "games_count", "value": val}).execute()
        return val
    except: return 0

# ================== 3. ОБРАБОТЧИКИ ГЛАВНОГО МЕНЮ ==================

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(m: types.Message, state: FSMContext):
    await state.finish()
    uname = m.from_user.username.lower() if m.from_user.username else None
    if not get_user(m.from_user.id):
        supabase.table("users").insert({
            "user_id": m.from_user.id, "name": m.from_user.first_name, "username": uname,
            "balance": 0.0, "wins": 0, "losses": 0
        }).execute()
    else:
        supabase.table("users").update({"username": uname, "name": m.from_user.first_name}).eq("user_id", m.from_user.id).execute()
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👤 Профиль", "🎮 Список Игр", "👛 Кошелек", "📊 ТОП", "ℹ️ Инфо", "🆘 Поддержка", "🚀 Чат проекта")
    await m.answer("🎲 <b>Добро пожаловать в DRH CASINO!</b>", reply_markup=kb)

# --- ПРОФИЛЬ И СТАТИСТИКА ---
@dp.message_handler(lambda m: m.text == "👤 Профиль", state="*")
async def profile(m: types.Message, state: FSMContext):
    await state.finish()
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0.0
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="my_stats"),
        types.InlineKeyboardButton("💸 Перевод", callback_data="tr_start")
    )
    await bot.send_photo(m.chat.id, photo=IMG_PROFILE, caption=f"<b>🖥️ ПРОФИЛЬ</b>\n\n🆔 ID: <code>{m.from_user.id}</code>\n👛 Баланс: <b>{bal} RUB</b>", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "my_stats", state="*")
async def show_stats(c: types.CallbackQuery):
    u = get_user(c.from_user.id)
    wins = u.get('wins', 0); losses = u.get('losses', 0); total = wins + losses
    winrate = round((wins / total) * 100, 1) if total > 0 else 0
    text = (
        f"📊 <b>ВАША СТАТИСТИКА</b>\n\n👤 Игрок: <b>{u['name']}</b>\n🆔 ID: <code>{c.from_user.id}</code>\n"
        f"🌐 Username: @{u['username'] if u['username'] else 'нет'}\n"
        f"--------------------------\n✅ Выигрышей: <b>{wins}</b>\n❌ Проигрышей: <b>{losses}</b>\n"
        f"📈 Winrate: <b>{winrate}%</b>\n🎮 Всего игр: <b>{total}</b>"
    )
    await c.message.answer(text); await c.answer()

# --- ИНФО (ПРАВИЛА) ---
@dp.message_handler(lambda m: m.text == "ℹ️ Инфо", state="*")
async def info_cmd(m: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "📜 <b>Информация DRH CASINO</b>\n\n"
        "• Любой вид мошенничества - <b>ОБНУЛЕНИЕ СРЕДСТВ</b> 🧨\n"
        "• Вести себя подобающе в игровом чате 🎮\n"
        "• Спор/угрозы и так далее в чате - мут на 3ч 📌\n"
        "• Спам в чате - 1 раз мут на 24ч 2 раз - черный список DRH CASINO 🚫\n"
        "• Любой вид фото 18+ - <b>ОБНУЛЕНИЕ СРЕДСТВ + ЧЕРНЫЙ СПИСОК DRH CASINO</b> 💢\n\n"
        "😉 Для решения проблемы напишите в поддержку!"
    )
    await bot.send_photo(m.chat.id, photo=IMG_RULES, caption=text)

# --- ИГРОВОЙ ЧАТ ---
@dp.message_handler(lambda m: m.text == "🚀 Чат проекта", state="*")
async def project_chat(m: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💬 <b>Игровой чат</b>\n\n"
        "В нашем чате Вы можете:\n\n"
        "• Общаться с игроками 🥰\n"
        "• Ставить ставки между игроками 💰\n"
        "• Найти себе друга/подругу 👥\n\n"
        "💘 И в принципе делать все что вашей душе угодно\n\n"
        f"📎 <b><a href='{CHAT_LINK}'>Перейти в наш игровой чат</a></b>"
    )
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➡️ В ЧАТ", url=CHAT_LINK))
    await bot.send_message(m.chat.id, text, reply_markup=kb, disable_web_page_preview=True)

# ================== 4. КОШЕЛЕК: ПОПОЛНЕНИЕ И ВЫВОД ==================

@dp.message_handler(lambda m: m.text == "👛 Кошелек", state="*")
async def wallet(m: types.Message, state: FSMContext):
    await state.finish()
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0.0
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Пополнить", callback_data="sbp_dep"),
        types.InlineKeyboardButton("📥 Вывод", callback_data="with_start")
    )
    await bot.send_photo(m.chat.id, photo=IMG_WALLET, caption=f"<b>👛 КОШЕЛЕК</b>\n\n🪙 Баланс: <b>{bal} RUB</b>", reply_markup=kb)

# ПОПОЛНЕНИЕ
@dp.callback_query_handler(lambda c: c.data == "sbp_dep", state="*")
async def sbp_dep(c: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await c.message.answer("💰 <b>Введите сумму пополнения в RUB:</b>")
    await DepositState.waiting_for_amount.set(); await c.answer()

@dp.message_handler(state=DepositState.waiting_for_amount)
async def sbp_amount(m: types.Message, state: FSMContext):
    try:
        amount = float(m.text.replace(',', '.'))
        if amount < 100: return await m.answer("❌ Минимальная сумма пополнения — 100 RUB.")
        await state.update_data(amount=amount)
        text = (
            f"🏆 <b>Пополнение баланса:</b>\n\n"
            f"ℹ️ Чтобы пополнить баланс пожалуйста скиньте желаемую сумму на реквизиты и ОБЯЗАТЕЛЬНО отправьте скриншот (не файл) чек оплаты!\n\n"
            f"🎯 Реквизиты - <code>{CARD_REQUISITES}</code>\n\n"
            f"⁉️ Ожидайте, баланс пополнится после проверки!\n\n"
            f"📸 <b>Жду ваш скриншот оплаты:</b>"
        )
        await m.answer(text); await DepositState.waiting_for_check.set()
    except: await m.answer("❌ Введите сумму числом.")

@dp.message_handler(content_types=['photo'], state=DepositState.waiting_for_check)
async def sbp_check(m: types.Message, state: FSMContext):
    data = await state.get_data(); amount = data.get('amount', 0); await state.finish()
    await m.answer("⏳ <b>Скриншот отправлен на проверку!</b>")
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton(f"✅ Одобрить {amount}₽", callback_data=f"adm_ok_{m.from_user.id}_{amount}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_no_{m.from_user.id}")
    )
    await bot.send_photo(ADMIN_ID, photo=m.photo[-1].file_id, 
                         caption=f"🔔 <b>ЧЕК ПОПОЛНЕНИЕ:</b> {m.from_user.mention}\nСумма: {amount} RUB", reply_markup=kb)

# ВЫВОД
@dp.callback_query_handler(lambda c: c.data == "with_start", state="*")
async def withdraw_start(c: types.CallbackQuery, state: FSMContext):
    await state.finish(); u = get_user(c.from_user.id)
    if not u or u['balance'] < 100: return await c.answer("❌ Минимальный вывод от 100 RUB", show_alert=True)
    await c.message.answer("💸 <b>Введите сумму для вывода:</b>\n(Минимум 100 RUB)"); await WithdrawState.waiting_for_amount.set(); await c.answer()

@dp.message_handler(state=WithdrawState.waiting_for_amount)
async def with_amount(m: types.Message, state: FSMContext):
    try:
        amount = float(m.text.replace(',', '.')); u = get_user(m.from_user.id)
        if amount < 100: return await m.answer("❌ Минимальная сумма — 100 RUB.")
        if amount > u['balance']: return await m.answer(f"❌ Недостаточно средств.")
        await state.update_data(with_amount=amount)
        await m.answer("🎯 <b>Введите реквизиты для получения выплаты:</b>"); await WithdrawState.waiting_for_details.set()
    except: await m.answer("❌ Введите сумму числом.")

@dp.message_handler(state=WithdrawState.waiting_for_details)
async def with_details(m: types.Message, state: FSMContext):
    data = await state.get_data(); amount = data.get('with_amount'); await state.finish()
    update_balance(m.from_user.id, -amount)
    await m.answer("✅ <b>Заявка на вывод создана!</b>\nОжидайте выплаты в течение 24 часов.")
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ Выплачено", callback_data=f"wd_ok_{m.from_user.id}_{amount}"),
        types.InlineKeyboardButton("❌ Отказать (Вернуть)", callback_data=f"wd_no_{m.from_user.id}_{amount}")
    )
    await bot.send_message(ADMIN_ID, f"📤 <b>ЗАЯВКА НА ВЫВОД</b>\n\nИгрок: {m.from_user.mention}\nСумма: <b>{amount} RUB</b>\nРеквизиты: <code>{m.text}</code>", reply_markup=kb)

# ================== 5. ВНУТРЕННИЕ ПЕРЕВОДЫ (P2P) ==================

@dp.callback_query_handler(lambda c: c.data == "tr_start", state="*")
async def transfer_start(c: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await c.message.answer("💸 <b>ПЕРЕВОД СРЕДСТВ</b>\n\nВведите @username игрока, которому хотите перевести деньги:")
    await TransferState.waiting_for_username.set(); await c.answer()

@dp.message_handler(state=TransferState.waiting_for_username)
async def tr_user(m: types.Message, state: FSMContext):
    target = get_user_by_username(m.text)
    if not target: return await m.answer("❌ Пользователь не найден в базе бота.")
    if target['user_id'] == m.from_user.id: return await m.answer("❌ Нельзя переводить самому себе.")
    await state.update_data(target_id=target['user_id'], target_name=target['name'])
    await m.answer(f"💰 Игрок найден: <b>{target['name']}</b>\nВведите сумму перевода:"); await TransferState.waiting_for_amount.set()

@dp.message_handler(state=TransferState.waiting_for_amount)
async def tr_amount(m: types.Message, state: FSMContext):
    try:
        amount = round(float(m.text.replace(',', '.')), 2); u = get_user(m.from_user.id)
        if amount <= 0: return await m.answer("❌ Сумма должна быть больше 0.")
        if u['balance'] < amount: return await m.answer(f"❌ Недостаточно средств.")
        
        data = await state.get_data(); target_id = data['target_id']
        update_balance(m.from_user.id, -amount); update_balance(target_id, amount); await state.finish()
        await m.answer(f"✅ Вы перевели <b>{amount} RUB</b> игроку <b>{data['target_name']}</b>!")
        try: await bot.send_message(target_id, f"🎁 Вам поступил перевод <b>{amount} RUB</b> от <b>{m.from_user.first_name}</b>!")
        except: pass
    except: await m.answer("❌ Ошибка в сумме.")

# ================== 6. АДМИН-ПАНЕЛЬ (ОБРАБОТКА РЕШЕНИЙ) ==================

@dp.callback_query_handler(lambda c: c.data.startswith('adm_') or c.data.startswith('wd_'))
async def admin_decision(c: types.CallbackQuery):
    data = c.data.split('_'); prefix, action, user_id = data[0], data[1], int(data[2])
    
    if prefix == 'adm': # Пополнение
        if action == 'ok':
            amount = float(data[3]); update_balance(user_id, amount); user = get_user(user_id)
            await bot.send_message(user_id, f"✅ <b>Зачислено: {amount} RUB</b>")
            try: await bot.send_photo(GROUP_ID, photo=IMG_SUCCESS_PAY, caption=f"💰 <b>ПОПОЛНЕНИЕ!</b>\n👤 Игрок: {user['name']}\n💵 Сумма: <b>{amount}₽</b>")
            except: pass
            await c.message.edit_caption(f"✅ ОДОБРЕНО")
        else:
            await bot.send_message(user_id, "❌ <b>Чек отклонен администратором.</b>"); await c.message.edit_caption(f"❌ ОТКЛОНЕНО")
            
    elif prefix == 'wd': # Вывод
        amount = float(data[3])
        if action == 'ok':
            await bot.send_message(user_id, f"💳 <b>Выплата {amount} RUB успешно выполнена!</b>"); await c.message.edit_text(c.message.text + f"\n\n✅ ВЫПЛАЧЕНО")
        else:
            update_balance(user_id, amount) # Возврат средств
            await bot.send_message(user_id, f"❌ <b>В выводе отказано.</b> Средства возвращены на баланс."); await c.message.edit_text(c.message.text + f"\n\n❌ ОТКАЗАНО")
    await c.answer()

# ================== 7. ИГРОВАЯ ЛОГИКА ==================

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
    _, cr_id, bet, g_type = c.data.split('_'); cr_id, bet, jo_id = int(cr_id), float(bet), c.from_user.id
    if jo_id == cr_id: return await c.answer("Нельзя с собой!", show_alert=True)
    cr_u, jo_u = get_user(cr_id), get_user(jo_id)
    if not jo_u or jo_u['balance'] < bet: return await c.answer("❌ Нет денег!", show_alert=True)
    
    update_balance(cr_id, -bet); update_balance(jo_id, -bet)
    emoji = GAMES_EMOJI[g_type]; await c.message.edit_text(f"🎲 <b>ИГРА: {g_type.upper()}</b>")
    
    m1 = await bot.send_dice(c.message.chat.id, emoji=emoji); v1 = m1.dice.value
    await asyncio.sleep(4)
    m2 = await bot.send_dice(c.message.chat.id, emoji=emoji); v2 = m2.dice.value
    
    win_sum = round((bet * 2) * 0.95, 2); game_num = get_game_number(); winner_id, loser_id = None, None
    if v1 > v2: update_balance(cr_id, win_sum); winner_id, loser_id = cr_id, jo_id
    elif v2 > v1: update_balance(jo_id, win_sum); winner_id, loser_id = jo_id, cr_id
    else: update_balance(cr_id, bet); update_balance(jo_id, bet)

    if winner_id:
        add_stat(winner_id, 'wins'); add_stat(loser_id, 'losses')

    res_text = (
        f"<b>{g_type.capitalize()} {emoji} №{game_num}</b>\n\n"
        f"📎 <a href='{CHAT_LINK}'>Наш чат</a>\n\n"
        f"💰 Выигрыш: <b>{win_sum if winner_id else '0'} RUB</b>\n\n"
        f"👥 Игроки:\n1️⃣ - {cr_u['name']}\n2️⃣ - {jo_u['name']}\n\n"
        f"⚡️ Победитель: {get_user(winner_id)['name'] if winner_id else 'Ничья (возврат)'}"
    )
    await bot.send_message(c.message.chat.id, res_text, disable_web_page_preview=True)

# ПРОЧИЕ КОМАНДЫ
@dp.message_handler(lambda m: m.text == "📊 ТОП", state="*")
async def top_players(m: types.Message, state: FSMContext):
    await state.finish()
    res = supabase.table("users").select("name, balance").order("balance", desc=True).limit(5).execute()
    text = "🏆 <b>ТОП-5 ИГРОКОВ:</b>\n\n"
    for i, user in enumerate(res.data, 1): text += f"{i}. {user['name']} — <b>{user['balance']}₽</b>\n"
    await m.answer(text)

@dp.message_handler(lambda m: m.text == "🆘 Поддержка", state="*")
async def support(m: types.Message, state: FSMContext):
    await state.finish(); await bot.send_photo(m.chat.id, photo=IMG_SUPPORT, caption=f"🆘 <b>Техническая поддержка</b>\n\nПишите администратору: @{ADMIN_USERNAME}")

@dp.message_handler(commands=['бал', 'b', 'bal'], state="*")
async def chat_bal(m: types.Message, state: FSMContext):
    u = get_user(m.from_user.id); bal = u['balance'] if u else 0.0; await m.reply(f"💰 Ваш баланс: <b>{bal} RUB</b>")

# Находим этот кусок в самом низу и меняем его:
if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    # Это нужно, чтобы Render видел живой порт
    threading.Thread(target=run_web, daemon=True).start()
    
    # Запускаем бота
    print("Бот запущен...")
    executor.start_polling(dp, skip_updates=True)
