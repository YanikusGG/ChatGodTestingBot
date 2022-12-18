import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime

from config import TOKEN


logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

kb_start = [
    [types.KeyboardButton(text="Расскажи о себе"), types.KeyboardButton(text="Сколько времени?")],
    [types.KeyboardButton(text="Повторюшка"), types.KeyboardButton(text="Калькулятор")],
    [types.KeyboardButton(text="Парсинг канала")],
]
keyboard_start = types.ReplyKeyboardMarkup(keyboard=kb_start, resize_keyboard=True)

class BotStates(StatesGroup):
    calculating = State()
    parsing = State()
    repeating = State()


@dp.message_handler(commands=['start', 'info'], state='*')
async def send_info(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Привет, " + message.chat.username + "!!\n" +
                         "Я бот-помощник, сделан в рамках курса ИПР (ВШЭ ПМИ). Автор: @yanikusgg",
                         reply_markup=keyboard_start)

@dp.message_handler(Text(["Расскажи о себе"]), state='*')
async def send_about(message: types.Message, state: FSMContext):
    await send_info(message, state)

@dp.message_handler(Text(["Сколько времени?"]), state='*')
async def send_time(message: types.Message, state: FSMContext):
    await state.finish()
    now = datetime.now().replace(microsecond=0)
    await message.answer("Сейчас: " + str(now),
                         reply_markup=keyboard_start)

@dp.message_handler(Text(["Повторюшка"]))
async def start_repeating(message: types.Message):
    await BotStates.repeating.set()
    await message.answer("Играем в повторюшку) если надоест, напиши `стоп`",
                         reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(Text(["стоп", "Стоп", "stop", "Stop"]), state=BotStates.repeating)
async def stop_repeating(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Отлично поиграли!!",
                         reply_markup=keyboard_start)

@dp.message_handler(state=BotStates.repeating)
async def send_repeat(message: types.Message, state: FSMContext):
    user_text = message.text
    await message.answer(user_text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
