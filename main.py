import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from bs4 import BeautifulSoup
from datetime import datetime
import re
import requests

from config import TOKEN, DEFAULT_POSTS_LIMIT, MAX_REQUESTS_PER_CHANNEL


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

@dp.message_handler(Text(["Калькулятор"]))
async def start_calculating(message: types.Message):
    await BotStates.calculating.set()
    await message.answer("Напиши арифметическое выражение, которое нужно вычислить",
                         reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=BotStates.calculating)
async def send_calculation(message: types.Message, state: FSMContext):
    await state.finish()
    user_text = message.text
    result = None
    try:
        result = eval(user_text, {"__builtins__": {}}, {})
    except Exception as e:
        print(e)
        result = 'Некорректное выражение!'
    await message.answer("Результат: " + str(result),
                         reply_markup=keyboard_start)

@dp.message_handler(Text(["Парсинг канала"]))
async def start_parsing(message: types.Message):
    await BotStates.parsing.set()
    await message.answer("Напиши, какой публичный канал нужно распарсить, в формате `@channel_name`",
                         reply_markup=types.ReplyKeyboardRemove())

async def get_last_image_id(channel):
    try:
        channel_url = f'https://t.me/s/{channel}'
        req = requests.get(channel_url)
        soup = BeautifulSoup(req.content.decode("utf-8"), 'html.parser')
        images = soup.find_all('a', {'class': 'tgme_widget_message_photo_wrap'})
        hrefs = [image.get('href')[len(channel_url)-1:] for image in images]
        return max(int(href[:-7] if href[-7:] == '?single' else href) for href in hrefs)
    except Exception as e:
        print(e)
        return 0

async def parse_image(channel, image_id):
    try:
        req = requests.get(f'https://t.me/s/{channel}/{image_id}')
        soup = BeautifulSoup(req.content.decode("utf-8"), 'html.parser')
        image = soup.find('a', {'class': 'tgme_widget_message_photo_wrap', 'href': f'https://t.me/{channel}/{image_id}'}) or \
                soup.find('a', {'class': 'tgme_widget_message_photo_wrap', 'href': f'https://t.me/{channel}/{image_id}?single'})
        if image is None:
            return None, None
        url = re.match(r".*background-image:url\('(.*?)'\).*", image.get('style')).group(1)
        if re.match(r".*/N.*", url):
            return None, None
        if image.get('href')[-7:] == '?single':
            text = image.parent.parent.parent.parent.find('div', {'class': 'tgme_widget_message_text'})
        else:
            text = image.parent.find('div', {'class': 'tgme_widget_message_text'})
        txt = None
        if text:
            txt = '\n'.join(text.stripped_strings)
        return url, txt
    except Exception as e:
        print(e)
        return None, None


async def get_images_from_channel(channel):
    try:
        posts_limit = DEFAULT_POSTS_LIMIT

        res_images = []
        image_id = await get_last_image_id(channel)
        request_count = 0

        while image_id > 0 and request_count < MAX_REQUESTS_PER_CHANNEL and len(res_images) < posts_limit:
            url, txt = await parse_image(channel, image_id)
            post_url = f'https://t.me/{channel}/{image_id}'
            image_id -= 1
            request_count += 1
            if url is None:
                continue
            if txt:
                caption = txt + '\n' + post_url
            else:
                caption = post_url
            res_images.append((url, caption))
        return res_images
    except Exception as e:
        print(e)
        return []

@dp.message_handler(state=BotStates.parsing)
async def send_parsed(message: types.Message, state: FSMContext):
    await state.finish()
    try:
        channel = message.text[1:]
        images = await get_images_from_channel(channel)
        if images:
            await message.answer(f"Последние картинки из канала @{channel}:")
            media = [types.input_media.InputMediaPhoto(media=image[0], caption=image[1]) for image in images]
            await message.answer_media_group(types.input_media.MediaGroup(media))
            await message.answer(f"Фух, распарсил! Я молодец!!",
                                 reply_markup=keyboard_start)
    except Exception as e:
        print(e)
        await message.answer("Произошла ошибка(",
                             reply_markup=keyboard_start)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
