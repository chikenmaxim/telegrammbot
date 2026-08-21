import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from telethon import TelegramClient
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import TimedOutAnswer

# ============================================================
#  НАСТРОЙКИ (ЗАМЕНИ НА СВОИ)
# ============================================================
BOT_TOKEN = "8276623524:AAEu2JbDRQJ-b3z_oQ5HCtJfPP4oGnSvN9k"
API_ID = 36452258  
API_HASH = "d583e25f462f72b255a648defa0421cb" 
ADMIN_ID = 1327466942  # Твой Telegram ID (узнай у @userinfobot)
# ============================================================

CHECKPOINT_ID = "53d94097-2b34-11ec-8467-ac1f6bf889c0"
API_URL = f"https://belarusborder.by/info/monitoring-new?token=test&checkpointId={CHECKPOINT_ID}"
POLL_INTERVAL = 300                   # 5 минут
DEFAULT_THRESHOLD = 10

# ---------- ИНИЦИАЛИЗАЦИЯ БОТА ----------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------- УПРАВЛЕНИЕ ДОСТУПОМ ----------
ALLOWED_FILE = "allowed_users.json"

def load_allowed_users():
    if os.path.exists(ALLOWED_FILE):
        with open(ALLOWED_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_allowed_users(users):
    with open(ALLOWED_FILE, 'w') as f:
        json.dump(list(users), f)

allowed_users = load_allowed_users()

class AllowedUserFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        user_id = message.from_user.id
        return user_id in allowed_users or user_id == ADMIN_ID

# ---------- ГЛОБАЛЬНЫЕ ДАННЫЕ ----------
app = None          # Telethon клиент
call_py = None      # PyTgCalls
user_data = {}      # user_id -> список машин {regnum, threshold, last_pos, alerted}

class Form(StatesGroup):
    waiting_regnum = State()
    waiting_threshold = State()

# ---------- КЛАВИАТУРЫ ----------
def main_keyboard(user_id=None):
    kb = [
        [KeyboardButton(text="➕ Мониторить машину")],
        [KeyboardButton(text="📋 Мои машины")],
        [KeyboardButton(text="❌ Удалить все машины")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="🔐 Панель админа")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def inline_machines_list(user_id):
    machines = user_data.get(user_id, [])
    if not machines:
        return None
    buttons = []
    for idx, m in enumerate(machines):
        regnum = m["regnum"]
        threshold = m["threshold"]
        text = f"🚗 {regnum} (порог {threshold})"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"del_{idx}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- ФУНКЦИИ ОЧЕРЕДИ ----------
def get_queue():
    try:
        r = requests.get(API_URL, timeout=10)
        return r.json().get("truckLiveQueue", [])
    except:
        return []

def find_position(regnum, queue):
    for item in queue:
        if item.get("regnum", "").upper() == regnum.upper():
            return item.get("order_id")
    return None

# ---------- ЗВОНОК ----------
async def make_call(user_id: int, duration: int = 5):
    try:
        await call_py.play(user_id, 'silence.wav')
        await asyncio.sleep(duration)
        await call_py.leave_call(user_id)
        return True
    except TimedOutAnswer:
        return False
    except Exception as e:
        print(f"Ошибка звонка: {e}")
        return False

# ---------- КОМАНДЫ АДМИНА ----------
@dp.message(Command("allow"))
async def allow_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только администратор может добавлять пользователей.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /allow <user_id>")
        return
    try:
        user_id = int(args[1])
        allowed_users.add(user_id)
        save_allowed_users(allowed_users)
        await message.answer(f"✅ Пользователь {user_id} добавлен в белый список.")
    except ValueError:
        await message.answer("❌ Некорректный ID.")

@dp.message(Command("deny"))
async def deny_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только администратор может удалять пользователей.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /deny <user_id>")
        return
    try:
        user_id = int(args[1])
        if user_id in allowed_users:
            allowed_users.remove(user_id)
            save_allowed_users(allowed_users)
            await message.answer(f"✅ Пользователь {user_id} удалён из белого списка.")
        else:
            await message.answer(f"ℹ️ Пользователь {user_id} не был в списке.")
    except ValueError:
        await message.answer("❌ Некорректный ID.")

@dp.message(Command("listusers"))
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только администратор может просматривать список.")
        return
    if allowed_users:
        users = "\n".join(str(uid) for uid in allowed_users)
        await message.answer(f"📋 Разрешённые пользователи:\n{users}")
    else:
        await message.answer("📋 Белый список пуст.")

@dp.message(lambda msg: msg.text == "🔐 Панель админа")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer(
        "🔐 **Панель администратора**\n\n"
        "Доступные команды:\n"
        "/allow <user_id> — добавить пользователя\n"
        "/deny <user_id> — удалить пользователя\n"
        "/listusers — показать всех разрешённых пользователей\n\n"
        "Пример: /allow 123456789"
    )

# ---------- ОСНОВНЫЕ ОБРАБОТЧИКИ ----------
@dp.message(Command("start"), AllowedUserFilter())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = []
    await message.answer(
        "🚚 **Бот мониторинга очереди на границе**\n\n"
        "Добавь машину для отслеживания. Когда твоя позиция в очереди станет меньше или равна заданному порогу, я позвоню тебе.\n\n"
        "Используй кнопки ниже:",
        reply_markup=main_keyboard(user_id)
    )

@dp.message(lambda msg: msg.text == "➕ Мониторить машину", AllowedUserFilter())
async def add_machine_button(message: types.Message, state: FSMContext):
    await message.answer("Введи номер машины (латиницей, без пробелов):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.waiting_regnum)

@dp.message(Form.waiting_regnum, AllowedUserFilter())
async def process_regnum(message: types.Message, state: FSMContext):
    regnum = message.text.strip().upper()
    if not regnum:
        await message.answer("❌ Введи номер.")
        return

    # Проверяем наличие машины в очереди
    queue = get_queue()
    pos = find_position(regnum, queue)
    if pos is None:
        await message.answer(
            f"❌ Машина {regnum} не найдена в текущей очереди.\n"
            "Добавление отменено. Попробуй позже или проверь правильность номера.",
            reply_markup=main_keyboard(message.from_user.id)
        )
        await state.clear()
        return

    # Машина найдена
    await state.update_data(regnum=regnum)
    await message.answer(
        f"✅ Машина {regnum} найдена в очереди (позиция {pos}).\n"
        f"Теперь введи порог (по умолчанию {DEFAULT_THRESHOLD})."
    )
    await state.set_state(Form.waiting_threshold)

@dp.message(Form.waiting_threshold, AllowedUserFilter())
async def process_threshold(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "":
        threshold = DEFAULT_THRESHOLD
    else:
        try:
            threshold = int(text)
            if threshold < 1:
                raise ValueError
        except:
            await message.answer("❌ Введи целое положительное число или оставь пустым.")
            return

    data = await state.get_data()
    regnum = data["regnum"]
    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = []

    # Проверка дубликата
    for m in user_data[user_id]:
        if m["regnum"] == regnum:
            await message.answer(f"❌ Машина {regnum} уже мониторится.")
            await state.clear()
            await message.answer("Возврат в главное меню.", reply_markup=main_keyboard(user_id))
            return

    user_data[user_id].append({
        "regnum": regnum,
        "threshold": threshold,
        "last_pos": None,
        "alerted": False
    })

    await message.answer(f"✅ Машина {regnum} добавлена с порогом {threshold}.")
    await state.clear()
    await message.answer("Что дальше?", reply_markup=main_keyboard(user_id))

@dp.message(lambda msg: msg.text == "📋 Мои машины", AllowedUserFilter())
async def my_machines(message: types.Message):
    user_id = message.from_user.id
    machines = user_data.get(user_id, [])
    if not machines:
        await message.answer("У тебя пока нет машин в мониторинге. Добавь через '➕ Мониторить машину'.", reply_markup=main_keyboard(user_id))
        return

    queue = get_queue()
    text = "📋 **Твои машины:**\n\n"
    for m in machines:
        regnum = m["regnum"]
        threshold = m["threshold"]
        pos = find_position(regnum, queue)
        pos_text = f"позиция {pos}" if pos is not None else "не в очереди"
        text += f"🚗 {regnum}: порог {threshold}, {pos_text}\n"

    keyboard = inline_machines_list(user_id)
    if keyboard:
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.answer(text, reply_markup=main_keyboard(user_id), parse_mode="Markdown")

@dp.message(lambda msg: msg.text == "❌ Удалить все машины", AllowedUserFilter())
async def delete_all_machines(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id] = []
        await message.answer("✅ Все машины удалены.", reply_markup=main_keyboard(user_id))
    else:
        await message.answer("У тебя нет машин.", reply_markup=main_keyboard(user_id))

# ---------- ОБРАБОТКА INLINE КНОПОК ----------
@dp.callback_query()
async def inline_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in allowed_users and user_id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    data = callback.data
    if data == "back_main":
        await callback.message.delete()
        await callback.message.answer("Главное меню:", reply_markup=main_keyboard(user_id))
        await callback.answer()
        return

    if data.startswith("del_"):
        try:
            idx = int(data.split("_")[1])
            if user_id in user_data and 0 <= idx < len(user_data[user_id]):
                removed = user_data[user_id].pop(idx)
                await callback.message.delete()
                await callback.message.answer(f"✅ Машина {removed['regnum']} удалена.", reply_markup=main_keyboard(user_id))
            else:
                await callback.answer("Машина не найдена.")
        except Exception:
            await callback.answer("Ошибка удаления.")
        await callback.answer()
        return

    await callback.answer()

# ---------- МОНИТОРИНГ ОЧЕРЕДИ ----------
async def monitor():
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        queue = get_queue()
        if not queue:
            continue

        for user_id, machines in list(user_data.items()):
            # Если пользователя нет в белом списке — удаляем его данные
            if user_id not in allowed_users and user_id != ADMIN_ID:
                user_data.pop(user_id, None)
                continue

            for m in machines:
                regnum = m["regnum"]
                threshold = m["threshold"]
                pos = find_position(regnum, queue)

                if pos is None:
                    if m["last_pos"] is not None:
                        await bot.send_message(user_id, f"🚫 {regnum} больше не в очереди.")
                    m["last_pos"] = None
                    m["alerted"] = False
                    continue

                if m["last_pos"] != pos:
                    await bot.send_message(user_id, f"🔄 {regnum}: позиция изменилась на **{pos}**")
                    m["last_pos"] = pos
                    m["alerted"] = False

                if pos <= threshold and not m["alerted"]:
                    m["alerted"] = True
                    await bot.send_message(user_id, f"🚨 **ОЧЕРЕДЬ ПОДОШЛА!**\nМашина {regnum} на {pos} месте. Звоню...")
                    success = await make_call(user_id, duration=5)
                    if success:
                        await bot.send_message(user_id, "✅ Звонок совершён.")
                    else:
                        await bot.send_message(user_id, "❌ Не удалось дозвониться.")

# ---------- ЗАПУСК ----------
async def main():
    global app, call_py
    print("🔑 Загружаем сессию...")
    app = TelegramClient("my_account", API_ID, API_HASH)
    await app.start()
    call_py = PyTgCalls(app)
    await call_py.start()
    print("✅ Аккаунт подключён, звонки готовы.")

    # Запускаем мониторинг и поллинг бота параллельно
    await asyncio.gather(
        monitor(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())