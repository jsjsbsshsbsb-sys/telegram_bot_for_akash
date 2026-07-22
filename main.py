import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from aiogram import Bot, Dispatcher, types, Router, F, BaseMiddleware
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage, Redis
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from aiogram.client.session.aiohttp import AiohttpSession

import aiofiles

# ---------- НАСТРОЙКИ ----------
TOKEN = "8564117995:AAEkciU1is19cCSwyz7UFZOktYKEXX2djiA"
ADMINS = [7041448219]  # список админов (int)
CHANNEL_ID = "@nastroytut"  # канал для подписки

# Redis (если не используется, можно заменить на MemoryStorage и простой кеш)
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# Файлы для хранения данных
USERS_FILE = "users.txt"
CONFIG_FILE = "config.json"  # для рекламы

# ---------- ЛОГИРОВАНИЕ ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- КЛАСС ДЛЯ ХРАНЕНИЯ НАСТРОЕК РЕКЛАМЫ ----------
class AdConfig:
    def __init__(self):
        self.photo_id: Optional[str] = None
        self.caption: Optional[str] = None
        self.enabled: bool = False
        self.delay: int = 0          # секунд
        self.position: str = "after"  # "before" или "after"

    def load(self):
        """Загрузить настройки из JSON-файла."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.photo_id = data.get("photo_id")
                    self.caption = data.get("caption")
                    self.enabled = data.get("enabled", False)
                    self.delay = data.get("delay", 0)
                    self.position = data.get("position", "after")
            except Exception as e:
                logger.error(f"Ошибка загрузки конфига: {e}")

    def save(self):
        """Сохранить настройки в JSON-файл."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "photo_id": self.photo_id,
                    "caption": self.caption,
                    "enabled": self.enabled,
                    "delay": self.delay,
                    "position": self.position
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения конфига: {e}")

ad_config = AdConfig()
ad_config.load()

# ---------- ИНИЦИАЛИЗАЦИЯ БОТА И ДИСПЕТЧЕРА ----------
# Настройка сессии с увеличенными таймаутами
session = AiohttpSession(timeout=60)
bot = Bot(token=TOKEN, session=session)

# Redis для FSM и кеша (если нет Redis – замените на MemoryStorage)
try:
    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    storage = RedisStorage(redis=redis)
except Exception as e:
    logger.warning("Redis недоступен, используем MemoryStorage")
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()

dp = Dispatcher(storage=storage)

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
async def save_user(user_id: int):
    """Асинхронно добавить пользователя в файл, если его там нет."""
    try:
        async with aiofiles.open(USERS_FILE, "a+", encoding="utf-8") as f:
            await f.seek(0)
            content = await f.read()
            if str(user_id) not in content.splitlines():
                await f.write(str(user_id) + "\n")
                logger.info(f"✅ Новый пользователь: {user_id}")
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")

async def get_users() -> List[int]:
    """Асинхронно получить список всех пользователей."""
    try:
        async with aiofiles.open(USERS_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            users = [int(line.strip()) for line in content.splitlines() if line.strip().isdigit()]
            logger.info(f"📊 Всего пользователей: {len(users)}")
            return users
    except FileNotFoundError:
        logger.warning("Файл users.txt не найден, создаю новый")
        return []
    except Exception as e:
        logger.error(f"Ошибка чтения users.txt: {e}")
        return []

async def is_subscribed(user_id: int) -> bool:
    """
    Проверяет подписку пользователя на канал.
    Результат кешируется в Redis на 30 секунд.
    """
    if not redis:
        # Если Redis не используется, проверяем напрямую
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            return member.status in (ChatMember.CREATOR, ChatMember.ADMINISTRATOR, ChatMember.MEMBER)
        except Exception as e:
            logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
            return False

    cache_key = f"sub:{user_id}"
    cached = await redis.get(cache_key)
    if cached is not None:
        return cached == b"1"

    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        is_sub = member.status in (ChatMember.CREATOR, ChatMember.ADMINISTRATOR, ChatMember.MEMBER)
        await redis.setex(cache_key, 30, b"1" if is_sub else b"0")
        return is_sub
    except Exception as e:
        logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
        return False

async def send_ad(user_id: int) -> bool:
    """Отправляет рекламное сообщение пользователю, если оно настроено."""
    if ad_config.enabled and ad_config.photo_id and ad_config.caption:
        try:
            await bot.send_photo(user_id, ad_config.photo_id, caption=ad_config.caption, parse_mode="HTML")
            logger.info(f"✅ Реклама отправлена пользователю {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки рекламы {user_id}: {e}")
            return False
    return False

# ---------- МИДЛВАРЬ ДЛЯ ПРОВЕРКИ ПОДПИСКИ ----------
class SubscriptionMiddleware(BaseMiddleware):
    """
    Проверяет подписку для всех сообщений и callback-запросов.
    Если не подписан – перенаправляет на экран с требованием подписки.
    """
    async def __call__(self, handler, event, data):
        # Пропускаем команду /start и /admin (там своя логика)
        if isinstance(event, Message) and event.text and event.text.startswith('/'):
            return await handler(event, data)

        user_id = event.from_user.id
        if not await is_subscribed(user_id):
            # Если не подписан – показываем сообщение с кнопкой подписки
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
                [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
            ])
            text = "❌ Вы не подписаны на наш канал!\nПодпишитесь и нажмите «Проверить»."

            if isinstance(event, Message):
                # Если это текстовое сообщение – отвечаем новым, но не пропускаем дальше
                await event.answer(text, reply_markup=keyboard)
                return
            elif isinstance(event, CallbackQuery):
                # Если это callback – редактируем текущее сообщение
                await event.message.edit_text(text, reply_markup=keyboard)
                await event.answer()
                return

        # Если подписан – передаём управление дальше
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

# ---------- МИДЛВАРЬ ДЛЯ ТРОТТЛИНГА ----------
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 2, period: int = 1):
        self.rate_limit = rate_limit
        self.period = period
        self.user_last_actions: Dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        now = time.time()
        if user_id in self.user_last_actions:
            if now - self.user_last_actions[user_id] < self.period:
                # Превышен лимит – игнорируем или отвечаем
                if isinstance(event, Message):
                    await event.answer("⏳ Слишком часто! Подождите секунду.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏳ Слишком часто!", show_alert=False)
                return
        self.user_last_actions[user_id] = now
        return await handler(event, data)

dp.message.middleware(ThrottlingMiddleware(rate_limit=3, period=1))
dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=3, period=1))

# ---------- СОСТОЯНИЯ ДЛЯ FSM ----------
class AdminStates(StatesGroup):
    waiting_ad_photo = State()           # установка фото для рекламы
    waiting_ad_delay = State()           # установка задержки
    waiting_newsletter_photo = State()   # получение фото для рассылки
    waiting_newsletter_text = State()    # получение текста для рассылки

# ---------- КЛАВИАТУРЫ (генерируются динамически) ----------
def get_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🍎 IPhone", callback_data="show_iphone_models")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="show_android_brands")],
        [InlineKeyboardButton(text="ℹ️ Разработчики", callback_data="show_developers")],
        [InlineKeyboardButton(text="🤳 Сотрудничество", callback_data="show_cooperation")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_iphone_models_keyboard() -> InlineKeyboardMarkup:
    models = [
        "iphone_7", "iphone_8", "iphone_10", "iphone_11", "iphone_12",
        "iphone_13", "iphone_14", "iphone_15", "iphone_16", "iphone_17"
    ]
    buttons = []
    for model in models:
        display = model.replace("_", " ").title()
        buttons.append([InlineKeyboardButton(text=f"⚙️ {display}", callback_data=f"model:{model}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_android_brands_keyboard() -> InlineKeyboardMarkup:
    brands = ["samsung", "realme", "poco", "redmi", "tecno", "huawei", "honor"]
    buttons = []
    for brand in brands:
        buttons.append([InlineKeyboardButton(text=brand.title(), callback_data=f"brand:{brand}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_model_keyboard(model_name: str) -> InlineKeyboardMarkup:
    # Для модели возвращаем только кнопку "Назад" – переход к списку моделей
    # Определяем, к какой категории относится модель (iPhone или Android)
    if model_name.startswith("iphone"):
        back_callback = "show_iphone_models"
    else:
        back_callback = "show_android_brands"
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_developers_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cooperation_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📢 Рассылка (фото)", callback_data="admin_newsletter_photo")],
        [InlineKeyboardButton(text="📢 Рассылка (текст)", callback_data="admin_newsletter_text")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🔄 Настройка рекламы", callback_data="admin_ad_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ad_settings_keyboard() -> InlineKeyboardMarkup:
    status_text = "🟢 ВКЛЮЧЕНА" if ad_config.enabled else "🔴 ВЫКЛЮЧЕНА"
    position_text = "ДО меню" if ad_config.position == "before" else "ПОСЛЕ меню"
    buttons = [
        [InlineKeyboardButton(text="📸 Установить фото", callback_data="admin_set_ad_photo")],
        [InlineKeyboardButton(text=f"⏱️ Задержка: {ad_config.delay} сек", callback_data="admin_set_ad_delay")],
        [InlineKeyboardButton(text=f"📌 Позиция: {position_text}", callback_data="admin_toggle_ad_position")],
        [InlineKeyboardButton(text=f"▶️/⏸️ Вкл/Выкл: {status_text}", callback_data="admin_toggle_ad_enabled")],
        [InlineKeyboardButton(text="👁️ Тест рекламы", callback_data="admin_test_ad")],
        [InlineKeyboardButton(text="🗑️ Удалить рекламу", callback_data="admin_delete_ad")],
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back_to_admin")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- ХЕНДЛЕРЫ КОМАНД ----------
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик /start – сохраняет пользователя и показывает приветствие."""
    await state.clear()
    await save_user(message.from_user.id)

    # Проверяем подписку
    if not await is_subscribed(message.from_user.id):
        # Отправляем сообщение с требованием подписки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
        ])
        await message.answer(
            "❌ Вы не подписаны на наш канал!\nПодпишитесь и нажмите «Проверить».",
            reply_markup=keyboard
        )
        return

    # Подписан – показываем главное меню с учётом рекламы
    # Реклама при /start
    if ad_config.enabled and ad_config.photo_id and ad_config.caption:
        if ad_config.position == "before":
            await send_ad(message.chat.id)
            if ad_config.delay > 0:
                await asyncio.sleep(ad_config.delay)
            await message.answer(
                "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\nВыберите своё устройство! 👇</blockquote>",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
        else:  # after
            await message.answer(
                "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\nВыберите своё устройство! 👇</blockquote>",
                reply_markup=get_main_keyboard(),
                parse_mode="HTML"
            )
            if ad_config.delay > 0:
                await asyncio.sleep(ad_config.delay)
            await send_ad(message.chat.id)
    else:
        await message.answer(
            "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\nВыберите своё устройство! 👇</blockquote>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Админ-панель."""
    await state.clear()
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав администратора!")
        return
    await message.answer("👑 Админ-панель. Выберите действие:", reply_markup=get_admin_keyboard())

# ---------- ОБРАБОТЧИКИ CALLBACK ----------
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):
    """Проверка подписки по кнопке."""
    user_id = call.from_user.id
    if await is_subscribed(user_id):
        # Обновляем кеш – он уже обновился в is_subscribed
        await call.message.edit_text(
            "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\nВыберите своё устройство! 👇</blockquote>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        await call.answer("✅ Вы подписаны!", show_alert=True)
    else:
        await call.answer("❌ Вы ещё не подписаны!", show_alert=True)

# ---------- ГЛАВНОЕ МЕНЮ ----------
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery):
    """Возврат в главное меню."""
    await call.message.edit_text(
        "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\nВыберите своё устройство! 👇</blockquote>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

# ---------- IPHONE МОДЕЛИ ----------
@dp.callback_query(F.data == "show_iphone_models")
async def show_iphone_models(call: CallbackQuery):
    """Показывает список iPhone."""
    await call.message.edit_text(
        "Выберите свой IPhone из списка:",
        reply_markup=get_iphone_models_keyboard()
    )
    await call.answer()

# ---------- ANDROID БРЕНДЫ ----------
@dp.callback_query(F.data == "show_android_brands")
async def show_android_brands(call: CallbackQuery):
    """Показывает список брендов Android."""
    await call.message.edit_text(
        "Выберите свой бренд Android:",
        reply_markup=get_android_brands_keyboard()
    )
    await call.answer()

# ---------- РАЗРАБОТЧИКИ ----------
@dp.callback_query(F.data == "show_developers")
async def show_developers(call: CallbackQuery):
    """Показывает информацию о разработчиках."""
    await call.message.edit_text(
        "✅Главные разработчики✅:\n\n @Acash_ff\n @JustF12",
        reply_markup=get_developers_keyboard()
    )
    await call.answer()

# ---------- СОТРУДНИЧЕСТВО ----------
@dp.callback_query(F.data == "show_cooperation")
async def show_cooperation(call: CallbackQuery):
    """Показывает контакты для сотрудничества."""
    await call.message.edit_text(
        "Пишите сюда 👇\n\n@Acash_ff",
        reply_markup=get_cooperation_keyboard()
    )
    await call.answer()

# ---------- ОТОБРАЖЕНИЕ НАСТРОЕК МОДЕЛИ ----------
# Словарь с настройками для всех моделей (собраны из оригинального кода)
MODEL_SETTINGS = {
    "iphone_7_base": "⚙️Настройки на IPhone 7 Base\n<blockquote>DPI 31\nОбзор 170\nКоллиматор 198\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 44</blockquote>",
    "iphone_7_plus": "⚙️Настройки на IPhone 7 Plus\n<blockquote>DPI 54\nОбзор 178\nКоллиматор 152\n2x 129\n4х 121\nСнайп прицел 137\nСвободный обзор 76\nКнопка огня: 46</blockquote>",
    "iphone_8_base": "⚙️Настройки на IPhone 8 Base\n<blockquote>Обзор: 167\nКоллиматор: 185\n2x Прицел: 181\n4x Прицел: 173\nКнопка: 50%\nDPI: Стандарт</blockquote>",
    "iphone_8_plus": "⚙️Настройки на IPhone 8 Plus\n<blockquote>DPI 31\nОбзор 100\nКоллиматор 187\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
    "iphone_10_base": "⚙️Настройки на IPhone X Base\n<blockquote>Dpi 31\nОбзор 177\nКоллиматор 195\n2x 198\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 49</blockquote>",
    "iphone_x_r": "⚙️Настройки на IPhone XR\n<blockquote>Dpi 120\nобзор 129\nКоллиматор 99\n2x 156\n4x 164\nСнайп прицел 100\nСвободный обзор 100\nКнопка огня 36</blockquote>",
    "iphone_10_s": "⚙️Настройки на IPhone XS\n<blockquote>Dpi 49\nОбзор 100\nКоллиматор 120\n2x 100\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
    "iphone_10_s_max": "⚙️Настройки на IPhone XS Max\n<blockquote>Обзор: 175\nКоллиматор: 185\n2x Прицел: 195\n4x Прицел: 173\nКнопка: 53%\nDPI: 31</blockquote>",
    "iphone_11_base": "⚙️Настройки на IPhone 11\n<blockquote>Обзор 149\nКоллиматор 150\n2х 200\n4х 180\nСнайп прицел 200\nСвободный обзор 200\nКнопка огня 39\nDPI: 31</blockquote>",
    "iphone_11_pro": "⚙️Настройки на IPhone 11 Pro\n<blockquote>обзор:170\nколлиматор:165\n2х прицел:155\n4х прицел:135\nснайперский прицел:110\nСвободная камера:130\n58-62 кнопка огня</blockquote>",
    "iphone_11_pro_max": "⚙️Настройки на IPhone 11 Pro Max\n<blockquote>Обзор 108\nКоллиматор 94\n2x 125\n4x 124\nСнайп прицел 66\nСвободный обзор 41\nDpi: 100\nКнопка огня: 45</blockquote>",
    "iphone_12_base": "⚙️Настройки IPhone 12\n<blockquote>Обзор: 165\nКоллиматор: 158\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 50\nDpi: 33</blockquote>",
    "iphone_12_mini": "⚙️Настройки IPhone 12 Mini\n<blockquote>Обзор: 158\nКоллиматор: 150\n2x: 135\n4x: 115\nСнайп прицел: 95\nСвободный обзор: 105\nКнопка огня: 48\nDpi: 42</blockquote>",
    "iphone_12_pro": "⚙️Настройки IPhone 12 Pro\n<blockquote>Обзор: 168\nКоллиматор: 160\n2x: 145\n4x: 125\nСнайп прицел: 100\nСвободный обзор: 112\nКнопка огня: 50\nDpi: 35</blockquote>",
    "iphone_12_pro_max": "⚙️Настройки IPhone 12 Pro Max\n<blockquote>Обзор: 172\nКоллиматор: 165\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 52\nDpi: стандарт</blockquote>",
    "iphone_13_base": "⚙️Настройки IPhone 13\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 120\nКнопка огня: 50\nDpi: стандарт</blockquote>",
    "iphone_13_mini": "⚙️Настройки IPhone 13 Mini\n<blockquote>Обзор: 170\nКоллиматор: 162\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 48\nDpi: Стандарт</blockquote>",
    "iphone_13_pro": "⚙️Настройки IPhone 13 Pro\n<blockquote>Обзор: 161\nКоллиматор: 168\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 50%\nDpi: 53</blockquote>",
    "iphone_13_pro_max": "⚙️Настройки IPhone 13 Pro Max\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 118\nКнопка огня: 52\nДпиай: 37</blockquote>",
    "iphone_14_base": "⚙️Настройки IPhone 14\n<blockquote>Обзор: 180\nКоллиматор: 172\n2x: 152\n4x: 132\nСнайп прицел: 107\nСвободный обзор: 120\nКнопка огня: 50\nДпиай: стандарт</blockquote>",
    "iphone_14_plus": "⚙️Настройки IPhone 14 Plus\n<blockquote>Обзор: 185\nКоллиматор: 176\n2x: 158\n4x: 138\nСнайп прицел: 110\nСвободный обзор: 125\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
    "iphone_14_pro": "⚙️Настройки IPhone 14 Pro\n<blockquote>Обзор: 187\nКоллиматор: 178\n2x: 160\n4x: 140\nСнайп прицел: 112\nСвободный обзор: 127\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
    "iphone_14_pro_max": "⚙️Настройки IPhone 14 Pro Max\n<blockquote>Обзор: 190\nКоллиматор: 182\n2x: 162\n4x: 142\nСнайп прицел: 115\nСвободный обзор: 130\nКнопка огня: 54\nDpi: стандарт</blockquote>",
    "iphone_15_base": "⚙️Настройки IPhone 15\n<blockquote>Обзор: 192\nКоллиматор: 184\n2x: 164\n4x: 144\nСнайп прицел: 117\nСвободный обзор: 132\nКнопка огня: 50\nDpi: стандарт</blockquote>",
    "iphone_15_plus": "⚙️Настройки IPhone 15 Plus\n<blockquote>Обзор: 195\nКоллиматор: 186\n2x: 166\n4x: 146\nСнайп прицел: 118\nСвободный обзор: 134\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
    "iphone_15_pro": "⚙️Настройки IPhone 15 Pro\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 120\nСвободный обзор: 136\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
    "iphone_15_pro_max": "⚙️Настройки IPhone 15 Pro Max\n<blockquote>Обзор: 200\nКоллиматор: 190\n2x: 170\n4x: 150\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 54\nDpi: Стандарт</blockquote>",
    "iphone_16_base": "⚙️Настройки IPhone 16\n<blockquote>Обзор: 195\nКоллиматор: 185\n2x: 165\n4x: 145\nСнайп прицел: 120\nСвободный обзор: 135\nКнопка огня: 50\nDpi: стандарт</blockquote>",
    "iphone_16_e": "⚙️Настройки IPhone 16e\n<blockquote>Обзор: 138\nКоллиматор: 128\n2x: 123\n4x: 108\nСнайп прицел: 98\nСвободный обзор: 118\nКнопка огня: 50\nDpi: стандарт</blockquote>",
    "iphone_16_plus": "⚙️Настройки IPhone 16 Plus\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 52\nDpi: стандарт</blockquote>",
    "iphone_16_pro": "⚙️Настройки IPhone 16 Pro\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 52\nDpi: стандарт</blockquote>",
    "iphone_16_pro_max": "⚙️Настройки IPhone 16 Pro Max\n<blockquote>Обзор: 148\nКоллиматор: 138\n2x: 133\n4x: 118\nСнайп прицел: 108\nСвободный обзор: 128\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
    "iphone_17_base": "⚙️Настройки IPhone 17\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 50%\nDpi: стандарт</blockquote>",
    "iphone_17_air": "⚙️Настройки IPhone 17 Air\n<blockquote>Обзор: 147\nКоллиматор: 137\n2x: 132\n4x: 117\nСнайп прицел: 107\nСвободный обзор: 127\nКнопка огня: 52\nDpi: стандарт</blockquote>",
    "iphone_17_pro": "⚙️Настройки IPhone 17 Pro\n<blockquote>Обзор: 150\nКоллиматор: 140\n2x: 135\n4x: 120\nСнайп прицел: 110\nСвободный обзор: 130\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
    "iphone_17_pro_max": "⚙️Настройки IPhone 17 Pro Max\n<blockquote>Обзор: 152\nКоллиматор: 142\n2x: 137\n4x: 122\nСнайп прицел: 112\nСвободный обзор: 132\nКнопка огня: 54\nDpi: стандарт</blockquote>",
    # Android модели
    "samsung_a_15": "<blockquote>обзор: 119\nколлиматор: 100\n2х: 172\n4х: 188\n8х: 120\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 582\nкнопка: 52</blockquote>",
    "samsung_a_10_s": "<blockquote>обзор: 199\nколлиматор: 190\n2х: 192\n4х: 193\n8х: 155\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 449\nкнопка: 39</blockquote>",
    "realme_12": "<blockquote>обзор: 188\nколлиматор: 180\n2х: 174\n4х: 168\n8х: 111\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 455\nкнопка: 50</blockquote>",
    "realme_8": "<blockquote>обзор: 177\nколлиматор: 159\n2х: 174\n4х: 181\n8х: 172\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 500\nкнопка: 48</blockquote>",
    "poco_x4_gt": "Настройки на Poco X4 GT\n<blockquote>обзор: 197\nколлиматор: 188\n2х: 178\n4х: 170\n8х: 155\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 520\nкнопка: 45</blockquote>",
    "redmi_note_14": "Настройки на Redmi Note 14\n<blockquote>обзор: 189\nколлиматор: 181\n2х: 175\n4х: 167\n8х: 111\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 40</blockquote>",
    "redmi_10_a": "Настройки на Redmi 10A\n<blockquote>обзор: 198\nколлиматор: 190\n2х: 177\n4х: 170\n8х: 110\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 51</blockquote>",
    "tecno_spark_30": "<blockquote>обзор: 183\nколлиматор: 178\n2х: 165\n4х: 171\n8х: 150\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 480\nкнопка: 40</blockquote>",
    "tecno_spark_7": "<blockquote>обзор: 192\nколлиматор: 188\n2х: 198\n4х: 155\n8х: 105\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 470\nкнопка: 37</blockquote>",
    "huawei_nova_8_i": "Настройки на Huawei Nova 8I\n<blockquote>обзор: 200\nколлиматор: 167\n2х: 174\n4х: 106\n8х: 91\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 458\nкнопка: 44</blockquote>",
    "honor_10_x_lite": "Настройки на Honor 10X Lite\n<blockquote>обзор: 192\nколлиматор: 177\n2х: 178\n4х: 154\n8х: 150\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 485\nкнопка: 39</blockquote>",
}

@dp.callback_query(F.data.startswith("model:"))
async def show_model_settings(call: CallbackQuery):
    """Показывает настройки для выбранной модели."""
    model_key = call.data.split(":", 1)[1]
    settings = MODEL_SETTINGS.get(model_key)
    if not settings:
        await call.answer("Настройки для этой модели не найдены.", show_alert=True)
        return

    # Определяем, к какой категории относится модель
    if model_key.startswith("iphone"):
        back_callback = "show_iphone_models"
    else:
        back_callback = "show_android_brands"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback)]
    ])
    await call.message.edit_text(
        settings,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await call.answer()

# ---------- АНДРОИД БРЕНДЫ (выбор конкретной модели) ----------
# Для Android брендов – показываем список моделей (как было в оригинале)
BRAND_MODELS = {
    "samsung": [("Samsung A15", "samsung_a_15"), ("Samsung A10S", "samsung_a_10_s")],
    "realme": [("Realme 12", "realme_12"), ("Realme 8", "realme_8")],
    "poco": [("Poco X4 GT", "poco_x4_gt")],
    "redmi": [("Redmi Note 14", "redmi_note_14"), ("Redmi 10A", "redmi_10_a")],
    "tecno": [("Tecno Spark 30", "tecno_spark_30"), ("Tecno Spark 7", "tecno_spark_7")],
    "huawei": [("Huawei Nova 8I", "huawei_nova_8_i")],
    "honor": [("Honor 10X Lite", "honor_10_x_lite")],
}

@dp.callback_query(F.data.startswith("brand:"))
async def show_brand_models(call: CallbackQuery):
    """Показывает список моделей для выбранного бренда."""
    brand = call.data.split(":", 1)[1]
    models = BRAND_MODELS.get(brand, [])
    if not models:
        await call.answer("Моделей для этого бренда нет.", show_alert=True)
        return

    buttons = []
    for display_name, model_key in models:
        buttons.append([InlineKeyboardButton(text=display_name, callback_data=f"model:{model_key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="show_android_brands")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(
        f"Выберите модель {brand.title()}:",
        reply_markup=keyboard
    )
    await call.answer()

# ---------- АДМИН-ПАНЕЛЬ ----------
# Проверка прав администратора для всех admin_* callback
@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback_filter(call: CallbackQuery, state: FSMContext):
    """Фильтр для админских callback – проверка прав."""
    if call.from_user.id not in ADMINS:
        await call.answer("❌ Нет доступа", show_alert=True)
        return
    # Передаём управление дальше в конкретные хендлеры

# ---------- АДМИН: НАСТРОЙКА РЕКЛАМЫ ----------
@dp.callback_query(F.data == "admin_ad_settings")
async def admin_ad_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
        f"Статус: {'🟢 ВКЛЮЧЕНА' if ad_config.enabled else '🔴 ВЫКЛЮЧЕНА'}\n"
        f"Позиция: {'ДО меню' if ad_config.position == 'before' else 'ПОСЛЕ меню'}\n"
        f"Задержка: {ad_config.delay} сек.\n"
        f"Фото: {'✅' if ad_config.photo_id else '❌'}\n"
        f"Подпись: {ad_config.caption[:50] + '...' if ad_config.caption else 'Отсутствует'}",
        reply_markup=get_ad_settings_keyboard()
    )
    await call.answer()

@dp.callback_query(F.data == "admin_set_ad_photo")
async def admin_set_ad_photo(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_ad_photo)
    await call.message.edit_text(
        "📸 Отправьте фото для рекламы при /start.\n"
        "✅ Добавьте подпись к фото!\n"
        "❌ Для отмены отправьте /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_ad_settings")]
        ])
    )
    await call.answer()

@dp.message(AdminStates.waiting_ad_photo, F.photo)
async def process_ad_photo(message: Message, state: FSMContext):
    if not message.caption:
        await message.answer("❌ Добавьте подпись к фото!")
        return
    ad_config.photo_id = message.photo[-1].file_id
    ad_config.caption = message.caption
    ad_config.save()
    await state.clear()
    await message.answer("✅ Фото и подпись для рекламы сохранены!")
    # Показываем настройки заново
    await admin_ad_settings(message, state)  # нужно вызвать как callback? проще отправить новое сообщение

@dp.callback_query(F.data == "admin_set_ad_delay")
async def admin_set_ad_delay(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_ad_delay)
    await call.message.edit_text(
        "⏱️ Введите задержку перед рекламой в СЕКУНДАХ (0-60):\n"
        "Пример: 0 - без задержки\n"
        "Пример: 3 - через 3 секунды\n"
        "❌ Для отмены отправьте /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_ad_settings")]
        ])
    )
    await call.answer()

@dp.message(AdminStates.waiting_ad_delay)
async def process_ad_delay(message: Message, state: FSMContext):
    try:
        delay = int(message.text)
        if delay < 0 or delay > 60:
            await message.answer("❌ Задержка должна быть от 0 до 60 секунд")
            return
        ad_config.delay = delay
        ad_config.save()
        await state.clear()
        await message.answer(f"✅ Задержка установлена: {delay} сек.")
        await admin_ad_settings(message, state)
    except ValueError:
        await message.answer("❌ Введите ЧИСЛО (например: 0, 3, 5)")

@dp.callback_query(F.data == "admin_toggle_ad_position")
async def admin_toggle_ad_position(call: CallbackQuery):
    ad_config.position = "after" if ad_config.position == "before" else "before"
    ad_config.save()
    await call.answer(f"✅ Позиция изменена на {'ДО' if ad_config.position == 'before' else 'ПОСЛЕ'} меню")
    await admin_ad_settings(call, None)

@dp.callback_query(F.data == "admin_toggle_ad_enabled")
async def admin_toggle_ad_enabled(call: CallbackQuery):
    if not ad_config.photo_id:
        await call.answer("❌ Сначала установите фото для рекламы!", show_alert=True)
        return
    ad_config.enabled = not ad_config.enabled
    ad_config.save()
    await call.answer(f"✅ Реклама {'ВКЛЮЧЕНА' if ad_config.enabled else 'ВЫКЛЮЧЕНА'}")
    await admin_ad_settings(call, None)

@dp.callback_query(F.data == "admin_test_ad")
async def admin_test_ad(call: CallbackQuery):
    if not ad_config.photo_id or not ad_config.caption:
        await call.answer("❌ Сначала установите фото для рекламы!", show_alert=True)
        return
    await call.answer("👁️ Отправляю тест...")
    if await send_ad(call.from_user.id):
        await call.message.answer("✅ Тестовая реклама отправлена!")
    else:
        await call.message.answer("❌ Ошибка отправки тестовой рекламы!")

@dp.callback_query(F.data == "admin_delete_ad")
async def admin_delete_ad(call: CallbackQuery):
    ad_config.photo_id = None
    ad_config.caption = None
    ad_config.enabled = False
    ad_config.save()
    await call.answer("🗑️ Реклама удалена!", show_alert=True)
    await admin_ad_settings(call, None)

# ---------- АДМИН: РАССЫЛКА ----------
@dp.callback_query(F.data == "admin_newsletter_photo")
async def admin_newsletter_photo(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_newsletter_photo)
    await call.message.edit_text(
        "📸 Отправьте фото для рассылки.\n"
        "✅ Добавьте подпись к фото!\n"
        "❌ Для отмены отправьте /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back_to_admin")]
        ])
    )
    await call.answer()

@dp.message(AdminStates.waiting_newsletter_photo, F.photo)
async def process_newsletter_photo(message: Message, state: FSMContext):
    if not message.caption:
        await message.answer("❌ Добавьте подпись к фото!")
        return
    # Сохраняем фото и подпись в state
    await state.update_data(newsletter_photo=message.photo[-1].file_id, newsletter_caption=message.caption)
    # Спрашиваем подтверждение
    users = await get_users()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отправить ВСЕМ", callback_data="admin_confirm_photo_newsletter")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="admin_back_to_admin")]
    ])
    await message.answer(
        f"📸 Начинаем рассылку?\n\n"
        f"Подпись: {message.caption}\n"
        f"Всего пользователей: {len(users)}\n\n"
        f"⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
        reply_markup=keyboard
    )
    await state.clear()

@dp.callback_query(F.data == "admin_confirm_photo_newsletter")
async def admin_confirm_photo_newsletter(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get("newsletter_photo")
    caption = data.get("newsletter_caption")
    if not photo_id or not caption:
        await call.answer("❌ Ошибка: данные рассылки не найдены", show_alert=True)
        return
    await call.answer("⏳ Идет рассылка...")
    await call.message.edit_text("⏳ Идет рассылка...\nЭто может занять некоторое время")

    users = await get_users()
    sent = 0
    failed = 0
    blocked = 0
    total = len(users)

    semaphore = asyncio.Semaphore(10)  # Ограничиваем параллелизм

    async def send_to_user(user_id):
        nonlocal sent, failed, blocked
        try:
            await bot.send_photo(user_id, photo_id, caption=caption, parse_mode="HTML")
            sent += 1
            logger.info(f"✅ Отправлено {user_id}")
        except Exception as e:
            failed += 1
            if "blocked" in str(e).lower():
                blocked += 1
            logger.error(f"❌ Ошибка отправки {user_id}: {e}")

    tasks = []
    for user_id in users:
        tasks.append(asyncio.create_task(send_to_user(user_id)))
        if len(tasks) >= 10:
            await asyncio.gather(*tasks)
            tasks = []

    if tasks:
        await asyncio.gather(*tasks)

    await call.message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"📸 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"👥 Всего в базе: {total}"
    )
    await state.clear()

@dp.callback_query(F.data == "admin_newsletter_text")
async def admin_newsletter_text(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_newsletter_text)
    await call.message.edit_text(
        "📝 Отправьте текст для рассылки.\n"
        "❌ Для отмены отправьте /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back_to_admin")]
        ])
    )
    await call.answer()

@dp.message(AdminStates.waiting_newsletter_text)
async def process_newsletter_text(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Отправьте текст!")
        return
    await state.update_data(newsletter_text=message.text)
    users = await get_users()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отправить ВСЕМ", callback_data="admin_confirm_text_newsletter")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="admin_back_to_admin")]
    ])
    await message.answer(
        f"📝 Начинаем рассылку?\n\n"
        f"Текст: {message.text}\n"
        f"Всего пользователей: {len(users)}\n\n"
        f"⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
        reply_markup=keyboard
    )
    await state.clear()

@dp.callback_query(F.data == "admin_confirm_text_newsletter")
async def admin_confirm_text_newsletter(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("newsletter_text")
    if not text:
        await call.answer("❌ Ошибка: текст не найден", show_alert=True)
        return
    await call.answer("⏳ Идет рассылка...")
    await call.message.edit_text("⏳ Идет рассылка...\nЭто может занять некоторое время")

    users = await get_users()
    sent = 0
    failed = 0
    blocked = 0
    total = len(users)

    semaphore = asyncio.Semaphore(10)

    async def send_to_user(user_id):
        nonlocal sent, failed, blocked
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1
            if "blocked" in str(e).lower():
                blocked += 1

    tasks = []
    for user_id in users:
        tasks.append(asyncio.create_task(send_to_user(user_id)))
        if len(tasks) >= 10:
            await asyncio.gather(*tasks)
            tasks = []
    if tasks:
        await asyncio.gather(*tasks)

    await call.message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"📝 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"👥 Всего в базе: {total}"
    )
    await state.clear()

# ---------- АДМИН: СТАТИСТИКА ----------
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    users = await get_users()
    await call.message.edit_text(
        f"📊 СТАТИСТИКА БОТА:\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"🆔 Ваш ID: {call.from_user.id}\n\n"
        f"📢 РЕКЛАМА ПРИ /START:\n"
        f"Статус: {'🟢 ВКЛЮЧЕНА' if ad_config.enabled else '🔴 ВЫКЛЮЧЕНА'}\n"
        f"Позиция: {'ДО меню' if ad_config.position == 'before' else 'ПОСЛЕ меню'}\n"
        f"Задержка: {ad_config.delay} сек.\n"
        f"Фото: {'✅' if ad_config.photo_id else '❌'}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_to_admin")]
        ])
    )
    await call.answer()

@dp.callback_query(F.data == "admin_users_list")
async def admin_users_list(call: CallbackQuery):
    users = await get_users()
    if not users:
        await call.message.edit_text("📭 Список пользователей пуст", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_to_admin")]
        ]))
        await call.answer()
        return

    # Отправляем список частями по 20 пользователей (редактировать не будем, просто отправим новое сообщение)
    text = "👥 Список пользователей:\n\n"
    for i, user_id in enumerate(users, 1):
        text += f"{i}. {user_id}\n"
        if i % 20 == 0:
            await call.message.answer(text)
            text = ""
    if text:
        await call.message.answer(text)
    await call.answer()

@dp.callback_query(F.data == "admin_back_to_admin")
async def admin_back_to_admin(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("👑 Админ-панель. Выберите действие:", reply_markup=get_admin_keyboard())
    await call.answer()

# ---------- ОБРАБОТЧИК ОТМЕНЫ (/cancel) ----------
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий для отмены.")
        return
    await state.clear()
    await message.answer("✅ Действие отменено.")

# ---------- ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК ----------
@dp.errors()
async def global_error_handler(update: types.Update, exception: Exception):
    logger.exception(f"Критическая ошибка: {exception}")
    # Можно отправить уведомление админам
    return True

# ---------- ЗАПУСК ----------
async def main():
    logger.info("Бот запускается...")
    # Удаляем вебхук, если использовался
    await bot.delete_webhook()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
