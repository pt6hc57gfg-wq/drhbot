import logging
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from supabase import create_client, Client

# ================== НАСТРОЙКИ (ЗАПОЛНИ!) ==================
SUPABASE_URL = "https://nlaadpwjsgwurbxtjyim.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sYWFkcHdqc2d3dXJieHRqeWltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzOTYzMTcsImV4cCI6MjA4NTk3MjMxN30.T3h8LomhBI7bjIdXRMQMwUlhVobFQzJhvMlfg_BYFBg"
TOKEN = "8390269866:AAHhAC9qEnUCauTQAVR23f9kHRWxUBwy6Nw"
ADMIN_ID = 8415442561             
ADMIN_USERNAME = "cemplex"       
GROUP_ID = -1003872240307       
CHAT_LINK = "https://t.me/drhcasino_chat"

WALLET_TON = "UQAwIecU8HyK5gI86k80a8jr2pPkGKOguOFggT2KLuvu_gZ7"
WALLET_USDT = "TH7BcXMjpmeYKVtxFyyFNnvAcycR7zFLii"

FEE = 0.95 

# Твои прямые ссылки
IMG_START = "https://i.postimg.cc/9FmD4tB3/fdab4dcb.jpg"
IMG_PROFILE = "https://i.postimg.cc/VvTM30tg/IMG-6661.png" 
IMG_WALLET = "https://i.postimg.cc/htmRmFP1/IMG_6662.png"
IMG_SUPPORT = "https://i.postimg.cc/VvTM30tg/IMG-6661.png"
IMG_TOPUP_CHAT = "https://i.postimg.cc/FHXk34V5/IMG-6654.png"
# ==========================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
dp = Dispatcher(bot, storage=MemoryStorage())

class DepositState(StatesGroup):
    waiting_for_amount = State()

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
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

# --- КЛАВИАТУРА ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("👤 Мой Профиль", "🎮 Список Игр")
    kb.add("💰 Кошелек", "🚀 Чат проекта")
    kb.add("📊 ТОП Игроков", "ℹ️ Правила", "🆘 Поддержка")
    return kb

# --- ОБРАБОТЧИКИ ---

@dp.message_handler(commands=['start'])
async def cmd_start(m: types.Message):
    register_user(m.from_user.id, m.from_user.first_name)
    welcome = (
        "🎲 <b>DRH CASINO приветствует тебя!</b>\n\n"
        "🕹️ <b>Наши игры:</b>\n"
        "Кубики, Баскет, Футбол, Дартс, Боулинг\n\n"
        "⁉️ <b>Как играть?</b>\n"
        "• Пополни баланс -> Перейди в чат -> <code>/game 100</code>\n\n"
        "Желаем удачи ❤️‍🔥"
    )
    ikb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ПЕРЕЙТИ В ЧАТ", url=CHAT_LINK))
    await bot.send_photo(m.chat.id, photo=IMG_START, caption=welcome, reply_markup=main_kb())

@dp.message_handler(lambda m: m.text == "👤 Мой Профиль")
async def profile(m: types.Message):
    u = get_user(m.from_user.id)
    bal = u['balance'] if u else 0
    txt = f"<b>🖥️ Профиль</b>\n\n🆔 ID: <code>{m.from_user.id}</code>\n👛 Баланс: <b>{bal} RUB</b>"
    await bot.send_photo(m.chat.id, photo=IMG_PROFILE, caption=txt)

@dp.message_handler(lambda m: m.text == "ℹ️ Правила")
async def rules(m: types.Message):
    txt = (
        "📜 <b>Правила DRH CASINO</b>\n\n"
        "• Не обманывать администрацию.\n"
        "• Уважать игроков.\n"
        "• Без спама и флуда.\n\n"
        "📌 Нарушение правил влечет за собой бан."
    )
    await m.answer(txt)

@dp.message_handler(lambda m: m.text == "🆘 Поддержка")
async def support(m: types.Message):
    txt = (
        "<b>🆘 Поддержка - DRH CASINO</b>\n\n"
        "😉 При проблеме сообщайте администрации, не паникуйте!\n"
        "📌 Пожалуйста, не флудите админам.\n\n"
        f"🆔 <b>Support - @{ADMIN_USERNAME}</b>"
    )
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👨‍💻 Связь", url=f"https://t.me/{ADMIN_USERNAME}"))
    await bot.send_photo(m.chat.id, photo=IMG_SUPPORT, caption=txt, reply_markup=kb)

@dp.message_handler(commands=['game'])
async def create_game(m: types.Message):
    if m.chat.id == m.from_user.id: return
    args = m.get_args().split()
    if not args: return await m.answer("⚠️ Пример: /game 100")
    try: bet = float(args[0])
    except: return
    u = get_user(m.from_user.id)
    if not u or u['balance'] < bet: return await m.answer("❌ Нет денег!")
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"Принять {bet}₽ 🎲", callback_data=f"j_{m.from_user.id}_{bet}"))
    await m.answer(f"🎮 <b>ИГРА!</b>\n👤 {m.from_user.mention}\n💰 Ставка: {bet}₽", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('j_'))
async def join_game(c: types.CallbackQuery):
    _, cr_id, bet = c.data.split('_')
    cr_id, bet, jo_id = int(cr_id), float(bet), c.from_user.id
    if jo_id == cr_id: return await c.answer("Нельзя играть с собой!", show_alert=True)
    cr_d, jo_d = get_user(cr_id), get_user(jo_id)
    if not cr_d or cr_d['balance'] < bet or not jo_d or jo_d['balance'] < bet:
        return await c.answer("Ошибка баланса!", show_alert=True)
    update_balance(cr_id, -bet); update_balance(jo_id, -bet)
    await c.message.edit_text(f"🎲 Битва: {cr_d['name']} VS {jo_d['name']}")
    m1 = await bot.send_dice(c.message.chat.id); v1 = m1.dice.value
    await asyncio.sleep(3)
    m2 = await bot.send_dice(c.message.chat.id); v2 = m2.dice.value
    await asyncio.sleep(2)
    win = round((bet * 2) * FEE, 2)
    if v1 > v2:
        update_balance(cr_id, win)
        res = f"🏆 Победил {cr_d['name']}! (+{win}₽)"
    elif v2 > v1:
        update_balance(jo_id, win)
        res = f"🏆 Победил {jo_d['name']}! (+{win}₽)"
    else:
        update_balance(cr_id, bet); update_balance(jo_id, bet)
        res = "🤝 Ничья! Возврат."
    await bot.send_message(c.message.chat.id, f"🏁 Итог: {v1}:{v2}\n\n{res}")

@dp.message_handler(lambda m: m.text == "💰 Кошелек")
async def wallet(m: types.Message):
    u = get_user(m.from_user.id)
    txt = f"💳 <b>КОШЕЛЕК</b>\nБаланс: <b>{u['balance'] if u else 0} RUB</b>"
    kb = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton("💎 Пополнить TON", callback_data="dep_ton"),
        types.InlineKeyboardButton("💵 Пополнить USDT", callback_data="dep_usdt")
    )
    await bot.send_photo(m.chat.id, photo=IMG_WALLET, caption=txt, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('dep_'))
async def dep_info(c: types.CallbackQuery):
    method, addr = ("TON", WALLET_TON) if "ton" in c.data else ("USDT", WALLET_USDT)
    await c.message.answer(f"📥 <b>{method}</b>\nАдрес: <code>{addr}</code>\n\nВведите сумму в рублях:")
    await DepositState.waiting_for_amount.set()

@dp.message_handler(state=DepositState.waiting_for_amount)
async def process_dep(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return
    await state.finish()
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ Да", callback_data=f"adm_p_{m.from_user.id}_{m.text}"),
        types.InlineKeyboardButton("❌ Нет", callback_data=f"adm_r_{m.from_user.id}")
    )
    await bot.send_message(ADMIN_ID, f"🔔 Пополнение {m.text}₽ от {m.from_user.id}", reply_markup=kb)
    await m.answer("🚀 Заявка отправлена!")

@dp.callback_query_handler(lambda c: c.data.startswith('adm_'))
async def admin_action(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    p = c.data.split('_')
    act, uid = p[1], int(p[2])
    if act == "p":
        amt = float(p[3])
        update_balance(uid, amt)
        await bot.send_message(uid, f"✅ Баланс пополнен на {amt}₽!")
        try: await bot.send_photo(GROUP_ID, photo=IMG_TOPUP_CHAT, caption=f"🔥 Пополнение на {amt} RUB!")
        except: pass
    await c.message.edit_text("Готово")

@dp.message_handler(lambda m: m.text == "📊 ТОП Игроков")
async def top(m: types.Message):
    res = supabase.table("users").select("name, balance").order("balance", desc=True).limit(10).execute()
    txt = "🏆 <b>ТОП-10 ИГРОКОВ:</b>\n\n"
    for i, p in enumerate(res.data, 1):
        txt += f"{i}. {p['name']} — {p['balance']}₽\n"
    await m.answer(txt)

@dp.message_handler(lambda m: m.text == "🚀 Чат проекта")
async def chat_btn(m: types.Message):
    await m.answer("Заходи и играй 👇", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 ЧАТ", url=CHAT_LINK)))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
