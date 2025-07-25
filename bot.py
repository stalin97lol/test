from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta
from google_service import log_absence, log_lunch_start, log_lunch_return, check_late_return

API_TOKEN = "8330237437:AAEgFAYGuvnHRwRykGdk5OX_KCSNZ018LCA"
ADMIN_CHAT_ID = 8330237437  # Замените на свой Telegram ID
AUTHORIZED_USERS = [8330237437]  # Добавьте сюда chat_id всех сотрудников

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AbsenceForm(StatesGroup):
    waiting_for_date = State()
    waiting_for_reason = State()

class LunchState(StatesGroup):
    on_lunch = State()

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("📅 Отсутствие"))
main_kb.add(KeyboardButton("🍽 Обед"))
main_kb.add(KeyboardButton("✅ Вернулся с обеда"))

@dp.message_handler(commands="start")
async def start_cmd(message: types.Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        await message.answer("⛔️ Доступ запрещён. Вы не авторизованы.")
        return
    await message.answer("Привет! Выбери действие:", reply_markup=main_kb)

@dp.message_handler(commands="profile")
async def profile(message: types.Message):
    user = message.from_user
    await message.answer(
        f"👤 Профиль:
"
        f"Имя: {user.full_name}
"
        f"Username: @{user.username or '—'}
"
        f"ID: {user.id}"
    )

@dp.message_handler(lambda msg: msg.text == "📅 Отсутствие")
async def absence_clicked(message: types.Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        return
    kb = InlineKeyboardMarkup(row_width=2)
    today = datetime.now()
    for i in range(5):
        day = today + timedelta(days=i)
        btn = InlineKeyboardButton(day.strftime("%d.%m.%Y"), callback_data=day.strftime("%Y-%m-%d"))
        kb.insert(btn)
    await message.answer("Выбери дату отсутствия:", reply_markup=kb)
    await AbsenceForm.waiting_for_date.set()

@dp.callback_query_handler(state=AbsenceForm.waiting_for_date)
async def chosen_date(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(absence_date=callback.data)
    await bot.send_message(callback.from_user.id, "Теперь напиши причину отсутствия:")
    await AbsenceForm.waiting_for_reason.set()
    await callback.answer()

@dp.message_handler(state=AbsenceForm.waiting_for_reason)
async def receive_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    absence_date = data["absence_date"]
    reason = message.text
    user = message.from_user.full_name
    log_absence(user, absence_date, reason)
    await bot.send_message(ADMIN_CHAT_ID, f"🚨 {user} будет отсутствовать {absence_date}\nПричина: {reason}")
    await message.answer("Готово! Информация сохранена.", reply_markup=main_kb)
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "🍽 Обед")
async def lunch_start(message: types.Message, state: FSMContext):
    user = message.from_user.full_name
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=45)
    await state.update_data(lunch_start=start_time.isoformat())
    log_lunch_start(user, start_time, end_time)
    await message.answer(f"⏳ Обед начат. Вернитесь до {end_time.strftime('%H:%M')}", reply_markup=main_kb)
    await LunchState.on_lunch.set()

@dp.message_handler(lambda msg: msg.text == "✅ Вернулся с обеда", state=LunchState.on_lunch)
async def lunch_return(message: types.Message, state: FSMContext):
    user = message.from_user.full_name
    return_time = datetime.now()
    data = await state.get_data()
    start_time = datetime.fromisoformat(data["lunch_start"])
    is_late = check_late_return(start_time, return_time)
    log_lunch_return(user, return_time, is_late)
    status = "⏱ Обед завершён вовремя." if not is_late else "⚠️ Обед затянулся более чем на 45 минут."
    await bot.send_message(ADMIN_CHAT_ID, f"{user} вернулся с обеда в {return_time.strftime('%H:%M')}\n{status}")
    await message.answer("Спасибо, что сообщили!", reply_markup=main_kb)
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)