# main.py
# Бот для настроек FreeFire с админ-панелью, рассылкой и рекламой
# Переписан с telebot на aiogram 3.x
# Хранилище пользователей — JSON

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== КОНФИГУРАЦИЯ =====
TOKEN = "8564117995:AAEkciU1is19cCSwyz7UFZOktYKEXX2djiA"
ADMINS = [7041448219]  # ID администраторов
CHANNEL_USERNAME = "@Acash_05"  # Канал для обязательной подписки
USERS_JSON_FILE = "users.json"  # JSON-файл с пользователями

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
# Данные для рассылки
newsletter_photo_id: Optional[str] = None
newsletter_caption: Optional[str] = None
newsletter_text: Optional[str] = None

# Данные для рекламы при /start
ad_photo_id: Optional[str] = None
ad_caption: Optional[str] = None
ad_enabled: bool = False  # Включена ли реклама
ad_delay: int = 0  # Задержка перед рекламой (в секундах)
ad_position: str = "after"  # "before" - до меню, "after" - после меню


# ===== FSM СОСТОЯНИЯ =====
class NewsletterStates(StatesGroup):
    """Состояния для рассылки"""
    waiting_photo = State()  # Ожидание фото для рассылки
    waiting_text = State()  # Ожидание текста для рассылки


class AdStates(StatesGroup):
    """Состояния для настройки рекламы"""
    waiting_photo = State()  # Ожидание фото для рекламы
    waiting_delay = State()  # Ожидание задержки


class SearchStates(StatesGroup):
    """Состояния для поиска пользователя"""
    waiting_id = State()  # Ожидание ввода ID


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С JSON =====
def load_users_data() -> List[Dict[str, Any]]:
    """Загрузка данных пользователей из JSON-файла"""
    try:
        with open(USERS_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Файл users.json не найден, создаю новый")
        return []
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON, создаю новый файл")
        return []


def save_users_data(data: List[Dict[str, Any]]) -> None:
    """Сохранение данных пользователей в JSON-файл"""
    with open(USERS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def save_user(user_id: int, first_name: str = "", username: str = "") -> None:
    """Сохранение/обновление информации о пользователе"""
    data = load_users_data()
    now = datetime.now().isoformat()

    # Ищем пользователя
    for user in data:
        if user["user_id"] == user_id:
            # Обновляем существующего
            user["first_name"] = first_name or user.get("first_name", "")
            user["username"] = username or user.get("username", "")
            user["last_active"] = now
            save_users_data(data)
            logger.info(f"✅ Обновлён пользователь: {user_id}")
            return

    # Новый пользователь
    new_user = {
        "user_id": user_id,
        "first_name": first_name,
        "username": username,
        "first_seen": now,
        "last_active": now
    }
    data.append(new_user)
    save_users_data(data)
    logger.info(f"✅ Новый пользователь: {user_id}")


async def get_users() -> List[str]:
    """Получение списка ID всех пользователей (для совместимости)"""
    data = load_users_data()
    return [str(u["user_id"]) for u in data]


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение полных данных пользователя по ID"""
    data = load_users_data()
    for user in data:
        if user["user_id"] == user_id:
            return user
    return None


async def get_users_count() -> int:
    """Количество пользователей"""
    return len(load_users_data())


# ===== ПРОВЕРКА ПОДПИСКИ =====
async def check_subscription(user_id: int) -> bool:
    """Проверка подписки пользователя на канал"""
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
        return False


# ===== ФУНКЦИЯ ОТПРАВКИ РЕКЛАМЫ =====
async def send_ad(user_id: int) -> bool:
    """Отправка рекламного сообщения пользователю"""
    if ad_enabled and ad_photo_id and ad_caption:
        try:
            await bot.send_photo(
                user_id,
                photo=ad_photo_id,
                caption=ad_caption,
                parse_mode="HTML"
            )
            logger.info(f"✅ Реклама отправлена пользователю {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки рекламы пользователю {user_id}: {e}")
            return False
    return False


# ===== КЛАВИАТУРЫ =====
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура меню"""
    keyboard = [
        [KeyboardButton(text="🍎IPhone🍎"), KeyboardButton(text="🤖Android🤖")],
        [KeyboardButton(text="ℹ️Разработчикиℹ️"), KeyboardButton(text="🤳Сотрудничество🤳")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    keyboard = [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для проверки подписки"""
    keyboard = [
        [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="🟢 Проверить", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    keyboard = [
        [InlineKeyboardButton(text="📢 Рассылка (фото)", callback_data="newsletter_photo")],
        [InlineKeyboardButton(text="📢 Рассылка (текст)", callback_data="newsletter_text")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="users_list")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="search_user")],
        [InlineKeyboardButton(text="🔄 НАСТРОЙКА РЕКЛАМЫ", callback_data="ad_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ad_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек рекламы"""
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    status_btn = "⏸️ Выключить рекламу" if ad_enabled else "▶️ Включить рекламу"
    
    keyboard = [
        [InlineKeyboardButton(text="📸 Установить фото", callback_data="set_ad_photo")],
        [InlineKeyboardButton(text="⏱️ Настроить задержку", callback_data="set_ad_delay")],
        [InlineKeyboardButton(text=f"📌 Позиция: {position_text}", callback_data="toggle_ad_position")],
        [InlineKeyboardButton(text=status_btn, callback_data="enable_ad" if not ad_enabled else "disable_ad")],
        [InlineKeyboardButton(text="👁️ Тест рекламы", callback_data="test_ad")],
        [InlineKeyboardButton(text="🗑️ Удалить рекламу", callback_data="delete_ad")],
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="back_to_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_iphone_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора iPhone"""
    keyboard = [
        [InlineKeyboardButton(text="⚙️IPhone 7", callback_data="iphone_7")],
        [InlineKeyboardButton(text="⚙️IPhone 8", callback_data="iphone_8")],
        [InlineKeyboardButton(text="⚙️IPhone X (10)", callback_data="iphone_10")],
        [InlineKeyboardButton(text="⚙️IPhone 11", callback_data="iphone_11")],
        [InlineKeyboardButton(text="⚙️IPhone 12", callback_data="iphone_12")],
        [InlineKeyboardButton(text="⚙️IPhone 13", callback_data="iphone_13")],
        [InlineKeyboardButton(text="⚙️IPhone 14", callback_data="iphone_14")],
        [InlineKeyboardButton(text="⚙️IPhone 15", callback_data="iphone_15")],
        [InlineKeyboardButton(text="⚙️IPhone 16", callback_data="iphone_16")],
        [InlineKeyboardButton(text="⚙️IPhone 17", callback_data="iphone_17")],
        [InlineKeyboardButton(text="🔙Назад🔙", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_android_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора Android"""
    keyboard = [
        [InlineKeyboardButton(text="Samsung", callback_data="samsung")],
        [InlineKeyboardButton(text="Realme", callback_data="realme")],
        [InlineKeyboardButton(text="Poco", callback_data="poco")],
        [InlineKeyboardButton(text="Redmi", callback_data="redmi")],
        [InlineKeyboardButton(text="Tecno", callback_data="tecno")],
        [InlineKeyboardButton(text="Huawei", callback_data="huawei")],
        [InlineKeyboardButton(text="Honor", callback_data="honor")],
        [InlineKeyboardButton(text="🔙Назад🔙", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline клавиатура с кнопкой назад"""
    keyboard = [[InlineKeyboardButton(text="🔙Назад🔙", callback_data="back")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ===== ОТПРАВКА ГЛАВНОГО МЕНЮ =====
async def send_main_menu(message: Message) -> None:
    """Отправка главного меню"""
    await message.answer(
        "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\n"
        "Выберите своё устройство! 👇</blockquote>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# ===== ОБРАБОТЧИК КОМАНДЫ /start =====
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработка команды /start"""
    await save_user(
        message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )
    
    # Проверка подписки
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "Вы не подписаны на наш телеграмм канал!\n"
            "Бот заработает после подписки!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    # Отправка рекламы в зависимости от настроек
    if ad_enabled and ad_photo_id and ad_caption:
        if ad_position == "before":
            # Реклама ДО меню
            await send_ad(message.from_user.id)
            if ad_delay > 0:
                await asyncio.sleep(ad_delay)
            await send_main_menu(message)
        else:
            # Реклама ПОСЛЕ меню
            await send_main_menu(message)
            if ad_delay > 0:
                await asyncio.sleep(ad_delay)
            await send_ad(message.from_user.id)
    else:
        await send_main_menu(message)


# ===== ПРОВЕРКА ПОДПИСКИ =====
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery) -> None:
    """Обработка проверки подписки"""
    if await check_subscription(callback.from_user.id):
        await callback.answer("✅ Вы подписаны! Можно пользоваться ботом.", show_alert=True)
        await send_main_menu(callback.message)
    else:
        await callback.answer("❌ Вы ещё не подписаны на канал!", show_alert=True)


# ===== АДМИН-ПАНЕЛЬ =====
@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Обработка команды /admin"""
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    await message.answer(
        "👑 Добро пожаловать в админ панель!\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


# ===== СТАТИСТИКА =====
@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery) -> None:
    """Обработка запроса статистики"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    users = await get_users()
    
    ad_status = "Включена" if ad_enabled else "Выключена"
    position_text = "До меню" if ad_position == "before" else "После меню"
    
    await callback.message.answer(
        f"📊 СТАТИСТИКА БОТА:\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"🆔 Ваш ID: {callback.from_user.id}\n\n"
        f"📢 РЕКЛАМА ПРИ /START:\n"
        f"Статус: {ad_status}\n"
        f"Позиция: {position_text}\n"
        f"Задержка: {ad_delay} сек.\n"
        f"Фото: {'✅' if ad_photo_id else '❌'}"
    )


# ===== СПИСОК ПОЛЬЗОВАТЕЛЕЙ =====
@router.callback_query(F.data == "users_list")
async def users_list_callback(callback: CallbackQuery) -> None:
    """Обработка запроса списка пользователей"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    users = await get_users()
    
    if not users:
        await callback.message.answer("📭 Список пользователей пуст")
        return
    
    # Отправляем список частями по 20 пользователей
    text = "👥 Список пользователей:\n\n"
    for i, user_id in enumerate(users, 1):
        text += f"{i}. {user_id}\n"
        if i % 20 == 0:
            await callback.message.answer(text)
            text = ""
    
    if text:
        await callback.message.answer(text)


# ===== ПОИСК ПОЛЬЗОВАТЕЛЯ =====
@router.callback_query(F.data == "search_user")
async def search_user_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало поиска пользователя по ID"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.answer(
        "🔍 Введите Telegram ID пользователя для поиска.\n\n"
        "❌ Для отмены отправьте /cancel"
    )
    await state.set_state(SearchStates.waiting_id)


@router.message(SearchStates.waiting_id, F.text)
async def process_search_id(message: Message, state: FSMContext) -> None:
    """Обработка введённого ID и вывод информации"""
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Нет доступа")
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуйте ещё раз или /cancel")
        return
    
    user_data = await get_user_by_id(user_id)
    if not user_data:
        await message.answer(f"❌ Пользователь с ID {user_id} не найден в базе.")
        await state.clear()
        return
    
    # Формируем вывод
    info = f"👤 **Информация о пользователе**\n\n"
    info += f"🆔 ID: `{user_data['user_id']}`\n"
    info += f"📛 Имя: {user_data.get('first_name', '—')}\n"
    info += f"🔹 Username: @{user_data.get('username', '—') if user_data.get('username') else '—'}\n"
    info += f"📅 Первое появление: {user_data.get('first_seen', '—')}\n"
    info += f"🕒 Последняя активность: {user_data.get('last_active', '—')}\n"
    
    await message.answer(info, parse_mode="Markdown")
    await state.clear()


@router.message(SearchStates.waiting_id, Command("cancel"))
async def cancel_search(message: Message, state: FSMContext) -> None:
    """Отмена поиска"""
    await message.answer("❌ Поиск отменён")
    await state.clear()


# ===== НАСТРОЙКИ РЕКЛАМЫ =====
@router.callback_query(F.data == "ad_settings")
async def ad_settings_callback(callback: CallbackQuery) -> None:
    """Обработка открытия настроек рекламы"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    status = "🟢 ВКЛЮЧЕНА" if ad_enabled else "🔴 ВЫКЛЮЧЕНА"
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    
    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: {status}\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    
    if ad_photo_id:
        ad_info += f"✅ Фото установлено\n"
        if ad_caption:
            ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"
    else:
        ad_info += f"❌ Фото не установлено\n"
    
    await callback.message.answer(ad_info, reply_markup=get_ad_settings_keyboard())


# ===== УСТАНОВКА ФОТО ДЛЯ РЕКЛАМЫ =====
@router.callback_query(F.data == "set_ad_photo")
async def set_ad_photo_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса установки фото для рекламы"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.answer(
        "📸 Отправьте фото для рекламы при /start.\n\n"
        "✅ Добавьте подпись к фото!\n"
        "❌ Для отмены отправьте /cancel"
    )
    await state.set_state(AdStates.waiting_photo)


@router.message(AdStates.waiting_photo, F.photo)
async def process_ad_photo(message: Message, state: FSMContext) -> None:
    """Обработка получения фото для рекламы"""
    global ad_photo_id, ad_caption
    
    if not message.caption:
        await message.answer("❌ Добавьте подпись к фото!")
        return
    
    ad_photo_id = message.photo[-1].file_id
    ad_caption = message.caption
    
    await message.answer(
        f"✅ Фото для рекламы установлено!\n\n"
        f"Подпись: {message.caption}\n\n"
        f"Теперь можете настроить другие параметры."
    )
    await state.clear()


@router.message(AdStates.waiting_photo, Command("cancel"))
async def cancel_ad_photo(message: Message, state: FSMContext) -> None:
    """Отмена установки фото для рекламы"""
    await message.answer("❌ Установка рекламы отменена")
    await state.clear()


# ===== НАСТРОЙКА ЗАДЕРЖКИ =====
@router.callback_query(F.data == "set_ad_delay")
async def set_ad_delay_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса установки задержки"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.answer(
        "⏱️ Введите задержку перед рекламой в СЕКУНДАХ (0-60):\n\n"
        "Пример: 0 - без задержки\n"
        "Пример: 3 - через 3 секунды\n"
        "❌ Для отмены отправьте /cancel"
    )
    await state.set_state(AdStates.waiting_delay)


@router.message(AdStates.waiting_delay, F.text)
async def process_ad_delay(message: Message, state: FSMContext) -> None:
    """Обработка получения задержки"""
    global ad_delay
    
    try:
        delay = int(message.text)
        if delay < 0 or delay > 60:
            await message.answer("❌ Задержка должна быть от 0 до 60 секунд")
            return
        
        ad_delay = delay
        await message.answer(f"✅ Задержка установлена: {delay} секунд(ы)")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите ЧИСЛО (например: 0, 3, 5)")


@router.message(AdStates.waiting_delay, Command("cancel"))
async def cancel_ad_delay(message: Message, state: FSMContext) -> None:
    """Отмена установки задержки"""
    await message.answer("❌ Настройка задержки отменена")
    await state.clear()


# ===== ПЕРЕКЛЮЧЕНИЕ ПОЗИЦИИ РЕКЛАМЫ =====
@router.callback_query(F.data == "toggle_ad_position")
async def toggle_ad_position_callback(callback: CallbackQuery) -> None:
    """Переключение позиции рекламы (до/после меню)"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    global ad_position
    ad_position = "after" if ad_position == "before" else "before"
    
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    await callback.answer(f"✅ Реклама будет {position_text.lower()}")
    
    # Обновляем сообщение с настройками
    status = "🟢 ВКЛЮЧЕНА" if ad_enabled else "🔴 ВЫКЛЮЧЕНА"
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    
    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: {status}\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    
    if ad_photo_id:
        ad_info += f"✅ Фото установлено\n"
        if ad_caption:
            ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"
    else:
        ad_info += f"❌ Фото не установлено\n"
    
    await callback.message.edit_text(ad_info, reply_markup=get_ad_settings_keyboard())


# ===== ТЕСТ РЕКЛАМЫ =====
@router.callback_query(F.data == "test_ad")
async def test_ad_callback(callback: CallbackQuery) -> None:
    """Тестовая отправка рекламы"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if not ad_photo_id or not ad_caption:
        await callback.answer("❌ Сначала установите фото для рекламы!", show_alert=True)
        return
    
    await callback.answer("👁️ Отправляю тестовое рекламное сообщение...")
    
    if await send_ad(callback.from_user.id):
        await callback.message.answer("✅ Тестовая реклама отправлена!")
    else:
        await callback.message.answer("❌ Ошибка отправки тестовой рекламы!")


# ===== ВКЛЮЧЕНИЕ/ВЫКЛЮЧЕНИЕ РЕКЛАМЫ =====
@router.callback_query(F.data == "enable_ad")
async def enable_ad_callback(callback: CallbackQuery) -> None:
    """Включение рекламы"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    global ad_enabled
    
    if not ad_photo_id:
        await callback.answer("❌ Сначала установите фото для рекламы!", show_alert=True)
        return
    
    ad_enabled = True
    await callback.answer("✅ Реклама при /start ВКЛЮЧЕНА!", show_alert=True)
    
    # Обновляем сообщение
    status = "🟢 ВКЛЮЧЕНА"
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    
    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: {status}\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    ad_info += f"✅ Фото установлено\n"
    ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"
    
    await callback.message.edit_text(ad_info, reply_markup=get_ad_settings_keyboard())


@router.callback_query(F.data == "disable_ad")
async def disable_ad_callback(callback: CallbackQuery) -> None:
    """Выключение рекламы"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    global ad_enabled
    ad_enabled = False
    await callback.answer("⏸️ Реклама при /start ВЫКЛЮЧЕНА!", show_alert=True)
    
    # Обновляем сообщение
    status = "🔴 ВЫКЛЮЧЕНА"
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    
    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: {status}\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    
    if ad_photo_id:
        ad_info += f"✅ Фото установлено\n"
        if ad_caption:
            ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"
    else:
        ad_info += f"❌ Фото не установлено\n"
    
    await callback.message.edit_text(ad_info, reply_markup=get_ad_settings_keyboard())


# ===== УДАЛЕНИЕ РЕКЛАМЫ =====
@router.callback_query(F.data == "delete_ad")
async def delete_ad_callback(callback: CallbackQuery) -> None:
    """Удаление рекламы"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    global ad_photo_id, ad_caption, ad_enabled
    
    ad_photo_id = None
    ad_caption = None
    ad_enabled = False
    
    await callback.answer("🗑️ Реклама удалена!", show_alert=True)
    
    # Обновляем сообщение
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    
    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: 🔴 ВЫКЛЮЧЕНА\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    ad_info += f"❌ Фото не установлено\n"
    
    await callback.message.edit_text(ad_info, reply_markup=get_ad_settings_keyboard())


# ===== НАЗАД В АДМИНКУ =====
@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_callback(callback: CallbackQuery) -> None:
    """Возврат в главное меню админки"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.delete()
    
    await callback.message.answer(
        "👑 Добро пожаловать в админ панель!\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


# ===== РАССЫЛКА С ФОТО =====
@router.callback_query(F.data == "newsletter_photo")
async def newsletter_photo_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса рассылки с фото"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.answer(
        "📸 Отправьте фото для рассылки.\n\n"
        "✅ Добавьте подпись к фото!\n"
        "❌ Для отмены отправьте /cancel"
    )
    await state.set_state(NewsletterStates.waiting_photo)


@router.message(NewsletterStates.waiting_photo, F.photo)
async def process_newsletter_photo(message: Message, state: FSMContext) -> None:
    """Обработка получения фото для рассылки"""
    global newsletter_photo_id, newsletter_caption
    
    if not message.caption:
        await message.answer("❌ Добавьте подпись к фото!")
        return
    
    newsletter_photo_id = message.photo[-1].file_id
    newsletter_caption = message.caption
    
    users = await get_users()
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, отправить ВСЕМ", callback_data="confirm_photo")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        f"📸 Начинаем рассылку?\n\n"
        f"Подпись: {message.caption}\n"
        f"Всего пользователей: {len(users)}\n\n"
        f"⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
        reply_markup=markup
    )
    await state.clear()


@router.message(NewsletterStates.waiting_photo, Command("cancel"))
async def cancel_newsletter_photo(message: Message, state: FSMContext) -> None:
    """Отмена рассылки с фото"""
    await message.answer("❌ Рассылка отменена")
    await state.clear()


# ===== РАССЫЛКА С ТЕКСТОМ =====
@router.callback_query(F.data == "newsletter_text")
async def newsletter_text_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса рассылки с текстом"""
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.answer(
        "📝 Отправьте текст для рассылки.\n\n"
        "❌ Для отмены отправьте /cancel"
    )
    await state.set_state(NewsletterStates.waiting_text)


@router.message(NewsletterStates.waiting_text, F.text)
async def process_newsletter_text(message: Message, state: FSMContext) -> None:
    """Обработка получения текста для рассылки"""
    global newsletter_text
    
    newsletter_text = message.text
    users = await get_users()
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, отправить ВСЕМ", callback_data="confirm_text")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        f"📝 Начинаем рассылку?\n\n"
        f"Текст: {message.text}\n"
        f"Всего пользователей: {len(users)}\n\n"
        f"⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
        reply_markup=markup
    )
    await state.clear()


@router.message(NewsletterStates.waiting_text, Command("cancel"))
async def cancel_newsletter_text(message: Message, state: FSMContext) -> None:
    """Отмена рассылки с текстом"""
    await message.answer("❌ Рассылка отменена")
    await state.clear()


# ===== ПОДТВЕРЖДЕНИЕ РАССЫЛКИ С ФОТО =====
@router.callback_query(F.data == "confirm_photo")
async def confirm_photo_callback(callback: CallbackQuery) -> None:
    """Выполнение рассылки с фото"""
    if callback.from_user.id not in ADMINS:
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "⏳ Идет рассылка ВСЕМ пользователям...\nЭто может занять некоторое время"
    )
    
    users = await get_users()
    sent = 0
    failed = 0
    blocked = 0
    total = len(users)
    
    for i, user_id in enumerate(users, 1):
        try:
            await bot.send_photo(
                int(user_id),
                photo=newsletter_photo_id,
                caption=newsletter_caption,
                parse_mode="HTML"
            )
            sent += 1
            logger.info(f"✅ [{i}/{total}] Отправлено пользователю {user_id}")
        except Exception as e:
            failed += 1
            error_text = str(e).lower()
            if "blocked" in error_text or "bot was blocked" in error_text:
                blocked += 1
                logger.warning(f"❌ [{i}/{total}] Пользователь {user_id} заблокировал бота")
            elif "chat not found" in error_text:
                logger.warning(f"❌ [{i}/{total}] Чат с {user_id} не найден")
            else:
                logger.error(f"❌ [{i}/{total}] Ошибка отправки {user_id}: {e}")
        
        # Задержка между сообщениями, чтобы не словить флуд-контроль
        if i % 20 == 0:
            await asyncio.sleep(1)
    
    await callback.message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"📸 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"👥 Всего в базе: {total}"
    )


# ===== ПОДТВЕРЖДЕНИЕ РАССЫЛКИ С ТЕКСТОМ =====
@router.callback_query(F.data == "confirm_text")
async def confirm_text_callback(callback: CallbackQuery) -> None:
    """Выполнение рассылки с текстом"""
    if callback.from_user.id not in ADMINS:
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "⏳ Идет рассылка ВСЕМ пользователям...\nЭто может занять некоторое время"
    )
    
    users = await get_users()
    sent = 0
    failed = 0
    blocked = 0
    total = len(users)
    
    for i, user_id in enumerate(users, 1):
        try:
            await bot.send_message(int(user_id), newsletter_text, parse_mode="HTML")
            sent += 1
            logger.info(f"✅ [{i}/{total}] Отправлено пользователю {user_id}")
        except Exception as e:
            failed += 1
            error_text = str(e).lower()
            if "blocked" in error_text or "bot was blocked" in error_text:
                blocked += 1
                logger.warning(f"❌ [{i}/{total}] Пользователь {user_id} заблокировал бота")
            elif "chat not found" in error_text:
                logger.warning(f"❌ [{i}/{total}] Чат с {user_id} не найден")
            else:
                logger.error(f"❌ [{i}/{total}] Ошибка отправки {user_id}: {e}")
        
        # Задержка между сообщениями
        if i % 20 == 0:
            await asyncio.sleep(1)
    
    await callback.message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"📝 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"👥 Всего в базе: {total}"
    )


# ===== ОТМЕНА =====
@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery) -> None:
    """Отмена рассылки"""
    if callback.from_user.id not in ADMINS:
        return
    
    await callback.answer()
    await callback.message.edit_text("❌ Рассылка отменена")


# ===== ОБРАБОТЧИКИ ДЛЯ IPHONE =====
# Эти обработчики создают вложенные меню для различных моделей iPhone

@router.callback_query(F.data == "iphone_7")
async def iphone_7_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 7", callback_data="iphone_7_base")],
        [InlineKeyboardButton(text="IPhone 7 Plus", callback_data="iphone_7_plus")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 7👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_7_base")
async def iphone_7_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 7 Base\n"
        "<blockquote>DPI 31\nОбзор 170\nКоллиматор 198\n2x 200\n4x 200\n"
        "Снайп прицел 200\nСвободный обзор 200\nКнопка 44</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_7_plus")
async def iphone_7_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 7 Plus\n"
        "<blockquote>DPI 54\nОбзор 178\nКоллиматор 152\n2x 129\n4х 121\n"
        "Снайп прицел 137\nСвободный обзор 76\nКнопка огня: 46</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_8")
async def iphone_8_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 8", callback_data="iphone_8_base")],
        [InlineKeyboardButton(text="IPhone 8 Plus", callback_data="iphone_8_plus")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 8👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_8_base")
async def iphone_8_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 8 Base\n"
        "<blockquote>Обзор: 167\nКоллиматор: 185\n2x Прицел: 181\n4x Прицел: 173\n"
        "Кнопка: 50%\nDPI: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_8_plus")
async def iphone_8_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 8 Plus\n"
        "<blockquote>DPI 31\nОбзор 100\nКоллиматор 187\n2x 200\n4x 200\n"
        "Снайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_10")
async def iphone_10_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone X", callback_data="iphone_10_base")],
        [InlineKeyboardButton(text="IPhone XR", callback_data="iphone_x_r")],
        [InlineKeyboardButton(text="IPhone XS", callback_data="iphone_10_s")],
        [InlineKeyboardButton(text="IPhone XS Max", callback_data="iphone_10_s_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone X👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_x_r")
async def iphone_x_r_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone XR\n"
        "<blockquote>Dpi 120\nобзор 129\nКоллиматор 99\n2x 156\n4x 164\n"
        "Снайп прицел 100\nСвободный обзор 100\nКнопка огня 36</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_10_base")
async def iphone_10_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone X Base\n"
        "<blockquote>Dpi 31\nОбзор 177\nКоллиматор 195\n2x 198\n4x 200\n"
        "Снайп прицел 200\nСвободный обзор 200\nКнопка 49</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_10_s")
async def iphone_10_s_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone XS\n"
        "<blockquote>Dpi 49\nОбзор 100\nКоллиматор 120\n2x 100\n4x 200\n"
        "Снайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_10_s_max")
async def iphone_10_s_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone XS Max\n"
        "<blockquote>Обзор: 175\nКоллиматор: 185\n2x Прицел: 195\n4x Прицел: 173\n"
        "Кнопка: 53%\nDPI: 31</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_11")
async def iphone_11_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 11", callback_data="iphone_11_base")],
        [InlineKeyboardButton(text="IPhone 11 Pro", callback_data="iphone_11_pro")],
        [InlineKeyboardButton(text="IPhone 11 Pro Max", callback_data="iphone_11_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 11👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_11_base")
async def iphone_11_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 11\n"
        "<blockquote>Обзор 149\nКоллиматор 150\n2х 200\n4х 180\n"
        "Снайп прицел 200\nСвободный обзор 200\nКнопка огня 39\nDPI: 31</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_11_pro")
async def iphone_11_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 11 Pro\n"
        "<blockquote>обзор:170\nколлиматор:165\n2х прицел:155\n4х прицел:135\n"
        "снайперский прицел:110\nСвободная камера:130\n58-62 кнопка огня</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_11_pro_max")
async def iphone_11_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки на IPhone 11 Pro Max\n"
        "<blockquote>Обзор 108\nКоллиматор 94\n2x 125\n4x 124\n"
        "Снайп прицел 66\nСвободный обзор 41\nDpi: 100\nКнопка огня: 45</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_12")
async def iphone_12_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 12", callback_data="iphone_12_base")],
        [InlineKeyboardButton(text="IPhone 12 Mini", callback_data="iphone_12_mini")],
        [InlineKeyboardButton(text="IPhone 12 Pro", callback_data="iphone_12_pro")],
        [InlineKeyboardButton(text="IPhone 12 Pro Max", callback_data="iphone_12_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 12👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_12_base")
async def iphone_12_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 12\n"
        "<blockquote>Обзор: 165\nКоллиматор: 158\n2x: 142\n4x: 122\n"
        "Снайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 50\nDpi: 33</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_12_mini")
async def iphone_12_mini_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 12 Mini\n"
        "<blockquote>Обзор: 158\nКоллиматор: 150\n2x: 135\n4x: 115\n"
        "Снайп прицел: 95\nСвободный обзор: 105\nКнопка огня: 48\nDpi: 42</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_12_pro")
async def iphone_12_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 12 Pro\n"
        "<blockquote>Обзор: 168\nКоллиматор: 160\n2x: 145\n4x: 125\n"
        "Снайп прицел: 100\nСвободный обзор: 112\nКнопка огня: 50\nDpi: 35</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_12_pro_max")
async def iphone_12_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 12 Pro Max\n"
        "<blockquote>Обзор: 172\nКоллиматор: 165\n2x: 148\n4x: 128\n"
        "Снайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_13")
async def iphone_13_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 13", callback_data="iphone_13_base")],
        [InlineKeyboardButton(text="IPhone 13 Mini", callback_data="iphone_13_mini")],
        [InlineKeyboardButton(text="IPhone 13 Pro", callback_data="iphone_13_pro")],
        [InlineKeyboardButton(text="IPhone 13 Pro Max", callback_data="iphone_13_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 13👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_13_base")
async def iphone_13_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 13\n"
        "<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\n"
        "Снайп прицел: 105\nСвободный обзор: 120\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_13_mini")
async def iphone_13_mini_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 13 Mini\n"
        "<blockquote>Обзор: 170\nКоллиматор: 162\n2x: 142\n4x: 122\n"
        "Снайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 48\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_13_pro")
async def iphone_13_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 13 Pro\n"
        "<blockquote>Обзор: 161\nКоллиматор: 168\n2x: 148\n4x: 128\n"
        "Снайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 50%\nDpi: 53</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_13_pro_max")
async def iphone_13_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 13 Pro Max\n"
        "<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\n"
        "Снайп прицел: 105\nСвободный обзор: 118\nКнопка огня: 52\nДпиай: 37</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_14")
async def iphone_14_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 14", callback_data="iphone_14_base")],
        [InlineKeyboardButton(text="IPhone 14 Plus", callback_data="iphone_14_plus")],
        [InlineKeyboardButton(text="IPhone 14 Pro", callback_data="iphone_14_pro")],
        [InlineKeyboardButton(text="IPhone 14 Pro Max", callback_data="iphone_14_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 14👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_14_base")
async def iphone_14_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 14\n"
        "<blockquote>Обзор: 180\nКоллиматор: 172\n2x: 152\n4x: 132\n"
        "Снайп прицел: 107\nСвободный обзор: 120\nКнопка огня: 50\nДпиай: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_14_plus")
async def iphone_14_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 14 Plus\n"
        "<blockquote>Обзор: 185\nКоллиматор: 176\n2x: 158\n4x: 138\n"
        "Снайп прицел: 110\nСвободный обзор: 125\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_14_pro")
async def iphone_14_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 14 Pro\n"
        "<blockquote>Обзор: 187\nКоллиматор: 178\n2x: 160\n4x: 140\n"
        "Снайп прицел: 112\nСвободный обзор: 127\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_14_pro_max")
async def iphone_14_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 14 Pro Max\n"
        "<blockquote>Обзор: 190\nКоллиматор: 182\n2x: 162\n4x: 142\n"
        "Снайп прицел: 115\nСвободный обзор: 130\nКнопка огня: 54\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_15")
async def iphone_15_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 15", callback_data="iphone_15_base")],
        [InlineKeyboardButton(text="IPhone 15 Plus", callback_data="iphone_15_plus")],
        [InlineKeyboardButton(text="IPhone 15 Pro", callback_data="iphone_15_pro")],
        [InlineKeyboardButton(text="IPhone 15 Pro Max", callback_data="iphone_15_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 15👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_15_base")
async def iphone_15_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 15\n"
        "<blockquote>Обзор: 192\nКоллиматор: 184\n2x: 164\n4x: 144\n"
        "Снайп прицел: 117\nСвободный обзор: 132\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_15_plus")
async def iphone_15_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 15 Plus\n"
        "<blockquote>Обзор: 195\nКоллиматор: 186\n2x: 166\n4x: 146\n"
        "Снайп прицел: 118\nСвободный обзор: 134\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_15_pro")
async def iphone_15_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 15 Pro\n"
        "<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\n"
        "Снайп прицел: 120\nСвободный обзор: 136\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_15_pro_max")
async def iphone_15_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 15 Pro Max\n"
        "<blockquote>Обзор: 200\nКоллиматор: 190\n2x: 170\n4x: 150\n"
        "Снайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 54\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_16")
async def iphone_16_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 16", callback_data="iphone_16_base")],
        [InlineKeyboardButton(text="IPhone 16e", callback_data="iphone_16_e")],
        [InlineKeyboardButton(text="IPhone 16 Plus", callback_data="iphone_16_plus")],
        [InlineKeyboardButton(text="IPhone 16 Pro", callback_data="iphone_16_pro")],
        [InlineKeyboardButton(text="IPhone 16 Pro Max", callback_data="iphone_16_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 16👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_16_base")
async def iphone_16_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 16\n"
        "<blockquote>Обзор: 195\nКоллиматор: 185\n2x: 165\n4x: 145\n"
        "Снайп прицел: 120\nСвободный обзор: 135\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_16_e")
async def iphone_16_e_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 16e\n"
        "<blockquote>Обзор: 138\nКоллиматор: 128\n2x: 123\n4x: 108\n"
        "Снайп прицел: 98\nСвободный обзор: 118\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_16_plus")
async def iphone_16_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 16 Plus\n"
        "<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\n"
        "Снайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_16_pro")
async def iphone_16_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 16 Pro\n"
        "<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\n"
        "Снайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_16_pro_max")
async def iphone_16_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 16 Pro Max\n"
        "<blockquote>Обзор: 148\nКоллиматор: 138\n2x: 133\n4x: 118\n"
        "Снайп прицел: 108\nСвободный обзор: 128\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_17")
async def iphone_17_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 17", callback_data="iphone_17_base")],
        [InlineKeyboardButton(text="IPhone 17 Air", callback_data="iphone_17_air")],
        [InlineKeyboardButton(text="IPhone 17 Pro", callback_data="iphone_17_pro")],
        [InlineKeyboardButton(text="IPhone 17 Pro Max", callback_data="iphone_17_pro_max")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите модель IPhone 17👇", reply_markup=markup)


@router.callback_query(F.data == "iphone_17_base")
async def iphone_17_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 17\n"
        "<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\n"
        "Снайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 50%\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_17_air")
async def iphone_17_air_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 17 Air\n"
        "<blockquote>Обзор: 147\nКоллиматор: 137\n2x: 132\n4x: 117\n"
        "Снайп прицел: 107\nСвободный обзор: 127\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_17_pro")
async def iphone_17_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 17 Pro\n"
        "<blockquote>Обзор: 150\nКоллиматор: 140\n2x: 135\n4x: 120\n"
        "Снайп прицел: 110\nСвободный обзор: 130\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "iphone_17_pro_max")
async def iphone_17_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⚙️Настройки IPhone 17 Pro Max\n"
        "<blockquote>Обзор: 152\nКоллиматор: 142\n2x: 137\n4x: 122\n"
        "Снайп прицел: 112\nСвободный обзор: 132\nКнопка огня: 54\nDpi: стандарт</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


# ===== ОБРАБОТЧИКИ ДЛЯ ANDROID =====
@router.callback_query(F.data == "samsung")
async def samsung_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Samsung A15", callback_data="samsung_a_15")],
        [InlineKeyboardButton(text="Samsung A10S", callback_data="samsung_a_10_s")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "samsung_a_15")
async def samsung_a_15_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "<blockquote>обзор: 119\nколлиматор: 100\n2х: 172\n4х: 188\n8х: 120\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 582\nкнопка: 52</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "samsung_a_10_s")
async def samsung_a_10_s_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "<blockquote>обзор: 199\nколлиматор: 190\n2х: 192\n4х: 193\n8х: 155\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 449\nкнопка: 39</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "redmi")
async def redmi_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Redmi Note 14", callback_data="redmi_note_14")],
        [InlineKeyboardButton(text="Redmi 10A", callback_data="redmi_10_a")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "redmi_note_14")
async def redmi_note_14_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Настройки на Redmi Note 14\n"
        "<blockquote>обзор: 189\nколлиматор: 181\n2х: 175\n4х: 167\n8х: 111\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 40</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "redmi_10_a")
async def redmi_10_a_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Настройки на Redmi 10A\n"
        "<blockquote>обзор: 198\nколлиматор: 190\n2х: 177\n4х: 170\n8х: 110\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 51</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "realme")
async def realme_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Realme 12", callback_data="realme_12")],
        [InlineKeyboardButton(text="Realme 8", callback_data="realme_8")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "realme_12")
async def realme_12_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "<blockquote>обзор: 188\nколлиматор: 180\n2х: 174\n4х: 168\n8х: 111\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 455\nкнопка: 50</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "realme_8")
async def realme_8_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "<blockquote>обзор: 177\nколлиматор: 159\n2х: 174\n4х: 181\n8х: 172\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 500\nкнопка: 48</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tecno")
async def tecno_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Tecno Spark 30", callback_data="tecno_spark_30")],
        [InlineKeyboardButton(text="Tecno Spark 7", callback_data="tecno_spark_7")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "tecno_spark_30")
async def tecno_spark_30_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "<blockquote>обзор: 183\nколлиматор: 178\n2х: 165\n4х: 171\n8х: 150\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 480\nкнопка: 40</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tecno_spark_7")
async def tecno_spark_7_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "<blockquote>обзор: 192\nколлиматор: 188\n2х: 198\n4х: 155\n8х: 105\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 470\nкнопка: 37</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "poco")
async def poco_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Poco X4 GT", callback_data="poco_x4_gt")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "poco_x4_gt")
async def poco_x4_gt_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Настройки на Poco X4 GT\n"
        "<blockquote>обзор: 197\nколлиматор: 188\n2х: 178\n4х: 170\n8х: 155\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 520\nкнопка: 45</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "huawei")
async def huawei_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Huawei Nova 8I", callback_data="huawei_nova_8_i")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "huawei_nova_8_i")
async def huawei_nova_8_i_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Настройки на Huawei Nova 8I\n"
        "<blockquote>обзор: 200\nколлиматор: 167\n2х: 174\n4х: 106\n8х: 91\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 458\nкнопка: 44</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "honor")
async def honor_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Honor 10X Lite", callback_data="honor_10_x_lite")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.answer("Выберите свою модель ниже👇", reply_markup=markup)


@router.callback_query(F.data == "honor_10_x_lite")
async def honor_10_x_lite_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Настройки на Honor 10X Lite\n"
        "<blockquote>обзор: 192\nколлиматор: 177\n2х: 178\n4х: 154\n8х: 150\n"
        "свободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 485\nкнопка: 39</blockquote>",
        reply_markup=get_back_inline_keyboard(),
        parse_mode="HTML"
    )


# ===== КНОПКА НАЗАД =====
@router.callback_query(F.data == "back")
async def back_callback(callback: CallbackQuery) -> None:
    """Возврат в главное меню"""
    await callback.answer()
    
    try:
        # Пробуем отправить с фото
        photo = FSInputFile("menu_logo.jpg")
        await callback.message.answer_photo(
            photo,
            caption="<blockquote>📋Вы вернулись в меню!📋</blockquote>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except:
        # Если фото нет, отправляем просто текст
        await callback.message.answer(
            "📋Вы вернулись в меню!📋",
            reply_markup=get_main_keyboard()
        )


# ===== ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ =====
@router.message(F.text == "🍎IPhone🍎")
async def iphone_handler(message: Message) -> None:
    """Обработка нажатия на кнопку iPhone"""
    try:
        photo = FSInputFile("iphone_sittings.jpg")
        await message.answer_photo(
            photo,
            caption="<blockquote>Выберите свой IPhone из списка!</blockquote>",
            reply_markup=get_iphone_keyboard(),
            parse_mode="HTML"
        )
    except:
        await message.answer(
            "Выберите свой IPhone из списка!",
            reply_markup=get_iphone_keyboard()
        )


@router.message(F.text == "🤖Android🤖")
async def android_handler(message: Message) -> None:
    """Обработка нажатия на кнопку Android"""
    try:
        photo = FSInputFile("android_sittings.jpg")
        await message.answer_photo(
            photo,
            caption="<blockquote>Выберите свой Android в списке👇</blockquote>",
            reply_markup=get_android_keyboard(),
            parse_mode="HTML"
        )
    except:
        await message.answer(
            "Выберите свой Android в списке👇",
            reply_markup=get_android_keyboard()
        )


@router.message(F.text == "ℹ️Разработчикиℹ️")
async def developers_handler(message: Message) -> None:
    """Обработка нажатия на кнопку Разработчики"""
    await message.answer(
        "✅Главные разработчики✅:\n\n @Acash_ff\n @JustF12",
        reply_markup=get_back_keyboard()
    )


@router.message(F.text == "🤳Сотрудничество🤳")
async def cooperation_handler(message: Message) -> None:
    """Обработка нажатия на кнопку Сотрудничество"""
    await message.answer(
        "Пишите сюда 👇\n\n@Acash_ff",
        reply_markup=get_back_keyboard()
    )


@router.message(F.text == "🔙 Назад")
async def back_button_handler(message: Message) -> None:
    """Обработка нажатия на кнопку Назад"""
    try:
        photo = FSInputFile("menu_logo.jpg")
        await message.answer_photo(
            photo,
            caption="<blockquote>📋Вы вернулись в меню!📋</blockquote>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except:
        await message.answer(
            "📋Вы вернулись в меню!📋",
            reply_markup=get_main_keyboard()
        )


@router.message(F.text)
async def default_text_handler(message: Message) -> None:
    """Обработка всех остальных текстовых сообщений"""
    # Игнорируем команды
    if message.text.startswith('/'):
        return
    
    # Для всех остальных сообщений показываем главное меню
    await send_main_menu(message)


# ===== ГЛАВНАЯ ФУНКЦИЯ =====
async def main():
    """Главная функция запуска бота"""
    # Регистрируем роутер
    dp.include_router(router)
    
    # Логируем информацию о запуске
    logger.info("=" * 50)
    logger.info("БОТ ЗАПУЩЕН")
    logger.info("=" * 50)
    logger.info(f"Админы: {ADMINS}")
    logger.info(f"Токен: {TOKEN[:10]}...")
    logger.info("=" * 50)
    logger.info("РЕКЛАМА ПРИ /START:")
    logger.info(f"Статус: {'ВКЛЮЧЕНА' if ad_enabled else 'ВЫКЛЮЧЕНА'}")
    logger.info(f"Позиция: {'ДО меню' if ad_position == 'before' else 'ПОСЛЕ меню'}")
    logger.info(f"Задержка: {ad_delay} сек.")
    logger.info(f"Фото: {'✅' if ad_photo_id else '❌'}")
    logger.info("=" * 50)
    logger.info("Для остановки нажмите Ctrl+C")
    logger.info("=" * 50)
    
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
