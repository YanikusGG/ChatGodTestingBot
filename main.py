import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
