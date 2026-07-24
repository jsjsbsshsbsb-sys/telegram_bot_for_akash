# main.py
# Бот для настроек FreeFire с админ-панелью, рассылкой и рекламой
# Все кнопки Inline, навигация через редактирование сообщений
# Поддерживается поиск пользователей по Telegram ID, username и внутреннему ID

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
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
newsletter_photo_id: Optional[str] = None
newsletter_caption: Optional[str] = None
newsletter_text: Optional[str] = None

ad_photo_id: Optional[str] = None
ad_caption: Optional[str] = None
ad_enabled: bool = False
ad_delay: int = 0
ad_position: str = "after"


# ===== FSM СОСТОЯНИЯ =====
class NewsletterStates(StatesGroup):
    waiting_photo = State()
    waiting_text = State()

class AdStates(StatesGroup):
    waiting_photo = State()
    waiting_delay = State()

class SearchStates(StatesGroup):
    waiting_query = State()


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С JSON =====
def load_users_data() -> List[Dict[str, Any]]:
    try:
        with open(USERS_JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_users_data(data: List[Dict[str, Any]]) -> None:
    with open(USERS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_next_internal_id(data: List[Dict[str, Any]]) -> int:
    """Генерирует следующий внутренний ID (максимальный + 1)"""
    if not data:
        return 1
    return max(user.get("internal_id", 0) for user in data) + 1

async def save_user(user_id: int, first_name: str = "", username: str = "") -> Tuple[int, bool]:
    """
    Сохраняет/обновляет пользователя.
    Возвращает (internal_id, is_new)
    """
    data = load_users_data()
    now = datetime.now().isoformat()
    is_new = False
    internal_id = None

    for user in data:
        if user["user_id"] == user_id:
            # Обновляем существующего
            user["first_name"] = first_name or user.get("first_name", "")
            user["username"] = username or user.get("username", "")
            user["last_active"] = now
            # Если у старого пользователя нет internal_id - добавляем
            if "internal_id" not in user:
                user["internal_id"] = get_next_internal_id(data)
            internal_id = user["internal_id"]
            save_users_data(data)
            logger.info(f"✅ Обновлён пользователь: {user_id}")
            return internal_id, False

    # Новый пользователь
    internal_id = get_next_internal_id(data)
    new_user = {
        "internal_id": internal_id,
        "user_id": user_id,
        "first_name": first_name,
        "username": username,
        "first_seen": now,
        "last_active": now
    }
    data.append(new_user)
    save_users_data(data)
    logger.info(f"✅ Новый пользователь: {user_id}, внутренний ID: {internal_id}")
    return internal_id, True

async def get_users() -> List[str]:
    return [str(u["user_id"]) for u in load_users_data()]

async def find_user_by_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Ищет пользователя по:
    - Telegram ID (если query — число)
    - внутреннему ID (если query — число и не найден по Telegram ID)
    - username (без учёта @, если строка)
    Возвращает полные данные пользователя или None
    """
    data = load_users_data()
    query = query.strip()

    # Попробуем как число (Telegram ID или внутренний ID)
    if query.isdigit():
        num = int(query)
        # Сначала ищем по Telegram ID
        for user in data:
            if user["user_id"] == num:
                return user
        # Затем по внутреннему ID
        for user in data:
            if user.get("internal_id") == num:
                return user
    else:
        # Ищем по username (убираем @, если есть)
        if query.startswith("@"):
            query = query[1:]
        query_lower = query.lower()
        for user in data:
            username = user.get("username", "")
            if username.lower() == query_lower:
                return user
    return None

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Оставлено для совместимости, но используем find_user_by_query"""
    for user in load_users_data():
        if user["user_id"] == user_id:
            return user
    return None


# ===== ПРОВЕРКА ПОДПИСКИ =====
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False


# ===== ФУНКЦИЯ ОТПРАВКИ РЕКЛАМЫ =====
async def send_ad(user_id: int) -> bool:
    if ad_enabled and ad_photo_id and ad_caption:
        try:
            await bot.send_photo(user_id, photo=ad_photo_id, caption=ad_caption, parse_mode="HTML")
            return True
        except:
            return False
    return False


# ===== INLINE КЛАВИАТУРЫ =====

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🍎 IPhone", callback_data="main_iphone"), InlineKeyboardButton(text="🤖 Android", callback_data="main_android")],
        [InlineKeyboardButton(
            text="Купить💎",
            url="https://t.me/GigaShop_tgbot",
            style="primary"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="🟢 Проверить", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📢 Рассылка (фото)", callback_data="newsletter_photo")],
        [InlineKeyboardButton(text="📢 Рассылка (текст)", callback_data="newsletter_text")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="users_list")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="search_user")],
        [InlineKeyboardButton(text="🔄 Настройка рекламы", callback_data="ad_settings")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ad_settings_keyboard() -> InlineKeyboardMarkup:
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
    keyboard = [
        [InlineKeyboardButton(text="⚙️ IPhone 7", callback_data="iphone_7")],
        [InlineKeyboardButton(text="⚙️ IPhone 8", callback_data="iphone_8")],
        [InlineKeyboardButton(text="⚙️ IPhone X (10)", callback_data="iphone_10")],
        [InlineKeyboardButton(text="⚙️ IPhone 11", callback_data="iphone_11")],
        [InlineKeyboardButton(text="⚙️ IPhone 12", callback_data="iphone_12")],
        [InlineKeyboardButton(text="⚙️ IPhone 13", callback_data="iphone_13")],
        [InlineKeyboardButton(text="⚙️ IPhone 14", callback_data="iphone_14")],
        [InlineKeyboardButton(text="⚙️ IPhone 15", callback_data="iphone_15")],
        [InlineKeyboardButton(text="⚙️ IPhone 16", callback_data="iphone_16")],
        [InlineKeyboardButton(text="⚙️ IPhone 17", callback_data="iphone_17")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_android_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="Samsung", callback_data="samsung")],
        [InlineKeyboardButton(text="Realme", callback_data="realme")],
        [InlineKeyboardButton(text="Poco", callback_data="poco")],
        [InlineKeyboardButton(text="Redmi", callback_data="redmi")],
        [InlineKeyboardButton(text="Tecno", callback_data="tecno")],
        [InlineKeyboardButton(text="Huawei", callback_data="huawei")],
        [InlineKeyboardButton(text="Honor", callback_data="honor")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])

def get_back_to_iphone_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]])

def get_back_to_android_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]])

def get_back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в админку", callback_data="back_to_admin")]])


# ===== ОТПРАВКА ГЛАВНОГО МЕНЮ (новое сообщение) =====
async def send_main_menu(message: Message) -> None:
    await message.answer(
        "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\n"
        "Выберите своё устройство! 👇</blockquote>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


# ===== ОБРАБОТЧИКИ КОМАНД =====
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Сохраняем пользователя и получаем его внутренний ID и флаг новизны
    internal_id, is_new = await save_user(
        message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username
    )

    # Проверка подписки
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "Вы не подписаны на наш телеграм канал!\nБот заработает после подписки!",
            reply_markup=get_subscription_keyboard()
        )
        return

    # Если пользователь новый — показываем приветствие с его внутренним ID
    if is_new:
        await message.answer(
            f"👋 Привет, {message.from_user.first_name or 'пользователь'}!\n\n"
            f"🎫 Твой внутренний ID в системе: <b>{internal_id}</b>\n"
            "Сохрани его, он может понадобиться для обращения в поддержку.",
            parse_mode="HTML"
        )

    # Отправка рекламы и меню
    if ad_enabled and ad_photo_id and ad_caption:
        if ad_position == "before":
            await send_ad(message.from_user.id)
            if ad_delay > 0:
                await asyncio.sleep(ad_delay)
            await send_main_menu(message)
        else:
            await send_main_menu(message)
            if ad_delay > 0:
                await asyncio.sleep(ad_delay)
            await send_ad(message.from_user.id)
    else:
        await send_main_menu(message)

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав администратора!")
        return
    await message.answer(
        "👑 Добро пожаловать в админ панель!\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )


# ===== ОБРАБОТЧИКИ CALLBACK =====

# Проверка подписки
@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery) -> None:
    if await check_subscription(callback.from_user.id):
        await callback.answer("✅ Вы подписаны! Можно пользоваться ботом.", show_alert=True)
        await callback.message.edit_text(
            "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\n"
            "Выберите своё устройство! 👇</blockquote>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Вы ещё не подписаны на канал!", show_alert=True)

# Главное меню (навигация)
@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\n"
        "Выберите своё устройство! 👇</blockquote>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "main_iphone")
async def main_iphone_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Выберите свой IPhone из списка:",
        reply_markup=get_iphone_keyboard()
    )

@router.callback_query(F.data == "main_android")
async def main_android_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Выберите свой Android из списка:",
        reply_markup=get_android_keyboard()
    )


# ===== МЕНЮ ВЫБОРА МОДЕЛЕЙ IPHONE =====

@router.callback_query(F.data == "iphone_7")
async def iphone_7_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 7", callback_data="iphone_7_base")],
        [InlineKeyboardButton(text="IPhone 7 Plus", callback_data="iphone_7_plus")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 7 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_8")
async def iphone_8_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 8", callback_data="iphone_8_base")],
        [InlineKeyboardButton(text="IPhone 8 Plus", callback_data="iphone_8_plus")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 8 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_10")
async def iphone_10_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone X", callback_data="iphone_10_base")],
        [InlineKeyboardButton(text="IPhone XR", callback_data="iphone_x_r")],
        [InlineKeyboardButton(text="IPhone XS", callback_data="iphone_10_s")],
        [InlineKeyboardButton(text="IPhone XS Max", callback_data="iphone_10_s_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone X 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_11")
async def iphone_11_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 11", callback_data="iphone_11_base")],
        [InlineKeyboardButton(text="IPhone 11 Pro", callback_data="iphone_11_pro")],
        [InlineKeyboardButton(text="IPhone 11 Pro Max", callback_data="iphone_11_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 11 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_12")
async def iphone_12_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 12", callback_data="iphone_12_base")],
        [InlineKeyboardButton(text="IPhone 12 Mini", callback_data="iphone_12_mini")],
        [InlineKeyboardButton(text="IPhone 12 Pro", callback_data="iphone_12_pro")],
        [InlineKeyboardButton(text="IPhone 12 Pro Max", callback_data="iphone_12_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 12 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_13")
async def iphone_13_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 13", callback_data="iphone_13_base")],
        [InlineKeyboardButton(text="IPhone 13 Mini", callback_data="iphone_13_mini")],
        [InlineKeyboardButton(text="IPhone 13 Pro", callback_data="iphone_13_pro")],
        [InlineKeyboardButton(text="IPhone 13 Pro Max", callback_data="iphone_13_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 13 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_14")
async def iphone_14_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 14", callback_data="iphone_14_base")],
        [InlineKeyboardButton(text="IPhone 14 Plus", callback_data="iphone_14_plus")],
        [InlineKeyboardButton(text="IPhone 14 Pro", callback_data="iphone_14_pro")],
        [InlineKeyboardButton(text="IPhone 14 Pro Max", callback_data="iphone_14_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 14 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_15")
async def iphone_15_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 15", callback_data="iphone_15_base")],
        [InlineKeyboardButton(text="IPhone 15 Plus", callback_data="iphone_15_plus")],
        [InlineKeyboardButton(text="IPhone 15 Pro", callback_data="iphone_15_pro")],
        [InlineKeyboardButton(text="IPhone 15 Pro Max", callback_data="iphone_15_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 15 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_16")
async def iphone_16_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 16", callback_data="iphone_16_base")],
        [InlineKeyboardButton(text="IPhone 16e", callback_data="iphone_16_e")],
        [InlineKeyboardButton(text="IPhone 16 Plus", callback_data="iphone_16_plus")],
        [InlineKeyboardButton(text="IPhone 16 Pro", callback_data="iphone_16_pro")],
        [InlineKeyboardButton(text="IPhone 16 Pro Max", callback_data="iphone_16_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 16 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "iphone_17")
async def iphone_17_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="IPhone 17", callback_data="iphone_17_base")],
        [InlineKeyboardButton(text="IPhone 17 Air", callback_data="iphone_17_air")],
        [InlineKeyboardButton(text="IPhone 17 Pro", callback_data="iphone_17_pro")],
        [InlineKeyboardButton(text="IPhone 17 Pro Max", callback_data="iphone_17_pro_max")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_iphone_menu")]
    ]
    await callback.message.edit_text("Выберите модель IPhone 17 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "back_to_iphone_menu")
async def back_to_iphone_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("Выберите свой IPhone из списка:", reply_markup=get_iphone_keyboard())

@router.callback_query(F.data == "back_to_android_menu")
async def back_to_android_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("Выберите свой Android из списка:", reply_markup=get_android_keyboard())

# ===== ОБРАБОТЧИКИ ДЛЯ КОНКРЕТНЫХ МОДЕЛЕЙ IPHONE =====

@router.callback_query(F.data == "iphone_7_base")
async def iphone_7_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 7 Base\n<blockquote>DPI 31\nОбзор 170\nКоллиматор 198\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 44</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_7_plus")
async def iphone_7_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 7 Plus\n<blockquote>DPI 54\nОбзор 178\nКоллиматор 152\n2x 129\n4х 121\nСнайп прицел 137\nСвободный обзор 76\nКнопка огня: 46</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_8_base")
async def iphone_8_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 8 Base\n<blockquote>Обзор: 167\nКоллиматор: 185\n2x Прицел: 181\n4x Прицел: 173\nКнопка: 50%\nDPI: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_8_plus")
async def iphone_8_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 8 Plus\n<blockquote>DPI 31\nОбзор 100\nКоллиматор 187\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_10_base")
async def iphone_10_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone X Base\n<blockquote>Dpi 31\nОбзор 177\nКоллиматор 195\n2x 198\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 49</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_x_r")
async def iphone_x_r_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone XR\n<blockquote>Dpi 120\nобзор 129\nКоллиматор 99\n2x 156\n4x 164\nСнайп прицел 100\nСвободный обзор 100\nКнопка огня 36</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_10_s")
async def iphone_10_s_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone XS\n<blockquote>Dpi 49\nОбзор 100\nКоллиматор 120\n2x 100\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_10_s_max")
async def iphone_10_s_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone XS Max\n<blockquote>Обзор: 175\nКоллиматор: 185\n2x Прицел: 195\n4x Прицел: 173\nКнопка: 53%\nDPI: 31</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_11_base")
async def iphone_11_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 11\n<blockquote>Обзор 149\nКоллиматор 150\n2х 200\n4х 180\nСнайп прицел 200\nСвободный обзор 200\nКнопка огня 39\nDPI: 31</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_11_pro")
async def iphone_11_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 11 Pro\n<blockquote>обзор:170\nколлиматор:165\n2х прицел:155\n4х прицел:135\nснайперский прицел:110\nСвободная камера:130\n58-62 кнопка огня</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_11_pro_max")
async def iphone_11_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки на IPhone 11 Pro Max\n<blockquote>Обзор 108\nКоллиматор 94\n2x 125\n4x 124\nСнайп прицел 66\nСвободный обзор 41\nDpi: 100\nКнопка огня: 45</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_12_base")
async def iphone_12_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 12\n<blockquote>Обзор: 165\nКоллиматор: 158\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 50\nDpi: 33</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_12_mini")
async def iphone_12_mini_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 12 Mini\n<blockquote>Обзор: 158\nКоллиматор: 150\n2x: 135\n4x: 115\nСнайп прицел: 95\nСвободный обзор: 105\nКнопка огня: 48\nDpi: 42</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_12_pro")
async def iphone_12_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 12 Pro\n<blockquote>Обзор: 168\nКоллиматор: 160\n2x: 145\n4x: 125\nСнайп прицел: 100\nСвободный обзор: 112\nКнопка огня: 50\nDpi: 35</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_12_pro_max")
async def iphone_12_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 12 Pro Max\n<blockquote>Обзор: 172\nКоллиматор: 165\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_13_base")
async def iphone_13_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 13\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 120\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_13_mini")
async def iphone_13_mini_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 13 Mini\n<blockquote>Обзор: 170\nКоллиматор: 162\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 48\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_13_pro")
async def iphone_13_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 13 Pro\n<blockquote>Обзор: 161\nКоллиматор: 168\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 50%\nDpi: 53</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_13_pro_max")
async def iphone_13_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 13 Pro Max\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 118\nКнопка огня: 52\nДпиай: 37</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_14_base")
async def iphone_14_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 14\n<blockquote>Обзор: 180\nКоллиматор: 172\n2x: 152\n4x: 132\nСнайп прицел: 107\nСвободный обзор: 120\nКнопка огня: 50\nДпиай: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_14_plus")
async def iphone_14_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 14 Plus\n<blockquote>Обзор: 185\nКоллиматор: 176\n2x: 158\n4x: 138\nСнайп прицел: 110\nСвободный обзор: 125\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_14_pro")
async def iphone_14_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 14 Pro\n<blockquote>Обзор: 187\nКоллиматор: 178\n2x: 160\n4x: 140\nСнайп прицел: 112\nСвободный обзор: 127\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_14_pro_max")
async def iphone_14_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 14 Pro Max\n<blockquote>Обзор: 190\nКоллиматор: 182\n2x: 162\n4x: 142\nСнайп прицел: 115\nСвободный обзор: 130\nКнопка огня: 54\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_15_base")
async def iphone_15_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 15\n<blockquote>Обзор: 192\nКоллиматор: 184\n2x: 164\n4x: 144\nСнайп прицел: 117\nСвободный обзор: 132\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_15_plus")
async def iphone_15_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 15 Plus\n<blockquote>Обзор: 195\nКоллиматор: 186\n2x: 166\n4x: 146\nСнайп прицел: 118\nСвободный обзор: 134\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_15_pro")
async def iphone_15_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 15 Pro\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 120\nСвободный обзор: 136\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_15_pro_max")
async def iphone_15_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 15 Pro Max\n<blockquote>Обзор: 200\nКоллиматор: 190\n2x: 170\n4x: 150\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 54\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_16_base")
async def iphone_16_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 16\n<blockquote>Обзор: 195\nКоллиматор: 185\n2x: 165\n4x: 145\nСнайп прицел: 120\nСвободный обзор: 135\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_16_e")
async def iphone_16_e_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 16e\n<blockquote>Обзор: 138\nКоллиматор: 128\n2x: 123\n4x: 108\nСнайп прицел: 98\nСвободный обзор: 118\nКнопка огня: 50\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_16_plus")
async def iphone_16_plus_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 16 Plus\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_16_pro")
async def iphone_16_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 16 Pro\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_16_pro_max")
async def iphone_16_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 16 Pro Max\n<blockquote>Обзор: 148\nКоллиматор: 138\n2x: 133\n4x: 118\nСнайп прицел: 108\nСвободный обзор: 128\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_17_base")
async def iphone_17_base_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 17\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 50%\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_17_air")
async def iphone_17_air_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 17 Air\n<blockquote>Обзор: 147\nКоллиматор: 137\n2x: 132\n4x: 117\nСнайп прицел: 107\nСвободный обзор: 127\nКнопка огня: 52\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_17_pro")
async def iphone_17_pro_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 17 Pro\n<blockquote>Обзор: 150\nКоллиматор: 140\n2x: 135\n4x: 120\nСнайп прицел: 110\nСвободный обзор: 130\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "iphone_17_pro_max")
async def iphone_17_pro_max_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ Настройки IPhone 17 Pro Max\n<blockquote>Обзор: 152\nКоллиматор: 142\n2x: 137\n4x: 122\nСнайп прицел: 112\nСвободный обзор: 132\nКнопка огня: 54\nDpi: стандарт</blockquote>",
        reply_markup=get_back_to_iphone_menu(),
        parse_mode="HTML"
    )


# ===== ОБРАБОТЧИКИ ДЛЯ ANDROID =====

@router.callback_query(F.data == "samsung")
async def samsung_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Samsung A15", callback_data="samsung_a_15")],
        [InlineKeyboardButton(text="Samsung A10S", callback_data="samsung_a_10_s")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Samsung 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "redmi")
async def redmi_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Redmi Note 14", callback_data="redmi_note_14")],
        [InlineKeyboardButton(text="Redmi 10A", callback_data="redmi_10_a")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Redmi 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "realme")
async def realme_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Realme 12", callback_data="realme_12")],
        [InlineKeyboardButton(text="Realme 8", callback_data="realme_8")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Realme 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "tecno")
async def tecno_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Tecno Spark 30", callback_data="tecno_spark_30")],
        [InlineKeyboardButton(text="Tecno Spark 7", callback_data="tecno_spark_7")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Tecno 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "poco")
async def poco_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Poco X4 GT", callback_data="poco_x4_gt")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Poco 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "huawei")
async def huawei_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Huawei Nova 8I", callback_data="huawei_nova_8_i")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Huawei 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "honor")
async def honor_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    keyboard = [
        [InlineKeyboardButton(text="Honor 10X Lite", callback_data="honor_10_x_lite")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_android_menu")]
    ]
    await callback.message.edit_text("Выберите свою модель Honor 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@router.callback_query(F.data == "back_to_android_menu")
async def back_to_android_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("Выберите свой Android из списка:", reply_markup=get_android_keyboard())

# ===== ОБРАБОТЧИКИ ДЛЯ КОНКРЕТНЫХ МОДЕЛЕЙ ANDROID =====

@router.callback_query(F.data == "samsung_a_15")
async def samsung_a_15_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>обзор: 119\nколлиматор: 100\n2х: 172\n4х: 188\n8х: 120\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 582\nкнопка: 52</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "samsung_a_10_s")
async def samsung_a_10_s_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>обзор: 199\nколлиматор: 190\n2х: 192\n4х: 193\n8х: 155\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 449\nкнопка: 39</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "redmi_note_14")
async def redmi_note_14_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Настройки на Redmi Note 14\n<blockquote>обзор: 189\nколлиматор: 181\n2х: 175\n4х: 167\n8х: 111\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 40</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "redmi_10_a")
async def redmi_10_a_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Настройки на Redmi 10A\n<blockquote>обзор: 198\nколлиматор: 190\n2х: 177\n4х: 170\n8х: 110\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 51</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "realme_12")
async def realme_12_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>обзор: 188\nколлиматор: 180\n2х: 174\n4х: 168\n8х: 111\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 455\nкнопка: 50</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "realme_8")
async def realme_8_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>обзор: 177\nколлиматор: 159\n2х: 174\n4х: 181\n8х: 172\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 500\nкнопка: 48</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "tecno_spark_30")
async def tecno_spark_30_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>обзор: 183\nколлиматор: 178\n2х: 165\n4х: 171\n8х: 150\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 480\nкнопка: 40</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "tecno_spark_7")
async def tecno_spark_7_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "<blockquote>обзор: 192\nколлиматор: 188\n2х: 198\n4х: 155\n8х: 105\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 470\nкнопка: 37</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "poco_x4_gt")
async def poco_x4_gt_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Настройки на Poco X4 GT\n<blockquote>обзор: 197\nколлиматор: 188\n2х: 178\n4х: 170\n8х: 155\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 520\nкнопка: 45</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "huawei_nova_8_i")
async def huawei_nova_8_i_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Настройки на Huawei Nova 8I\n<blockquote>обзор: 200\nколлиматор: 167\n2х: 174\n4х: 106\n8х: 91\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 458\nкнопка: 44</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "honor_10_x_lite")
async def honor_10_x_lite_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Настройки на Honor 10X Lite\n<blockquote>обзор: 192\nколлиматор: 177\n2х: 178\n4х: 154\n8х: 150\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 485\nкнопка: 39</blockquote>",
        reply_markup=get_back_to_android_menu(),
        parse_mode="HTML"
    )


# ===== АДМИН-ПАНЕЛЬ (все callback с редактированием) =====

@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    users = await get_users()
    ad_status = "Включена" if ad_enabled else "Выключена"
    position_text = "До меню" if ad_position == "before" else "После меню"
    text = (f"📊 СТАТИСТИКА БОТА:\n\n"
            f"👥 Всего пользователей: {len(users)}\n"
            f"🆔 Ваш ID: {callback.from_user.id}\n\n"
            f"📢 РЕКЛАМА ПРИ /START:\n"
            f"Статус: {ad_status}\n"
            f"Позиция: {position_text}\n"
            f"Задержка: {ad_delay} сек.\n"
            f"Фото: {'✅' if ad_photo_id else '❌'}")
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "users_list")
async def users_list_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    users = await get_users()
    if not users:
        await callback.message.edit_text("📭 Список пользователей пуст", reply_markup=get_admin_keyboard())
        return
    text = "👥 Список пользователей:\n\n" + "\n".join(f"{i+1}. {uid}" for i, uid in enumerate(users))
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "search_user")
async def search_user_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "🔍 Введите запрос для поиска пользователя.\n"
        "Можно ввести:\n"
        "• Telegram ID (число)\n"
        "• Внутренний ID (число)\n"
        "• Username (с @ или без)\n\n"
        "❌ Для отмены отправьте /cancel",
        reply_markup=None
    )
    await state.set_state(SearchStates.waiting_query)

@router.message(SearchStates.waiting_query, F.text)
async def process_search_query(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in ADMINS:
        return
    query = message.text.strip()
    if not query:
        await message.answer("❌ Введите непустой запрос.")
        return

    user_data = await find_user_by_query(query)
    if not user_data:
        await message.answer(f"❌ Пользователь по запросу '{query}' не найден.")
        await state.clear()
        return

    info = (f"👤 **Информация о пользователе**\n\n"
            f"🆔 Внутренний ID: `{user_data.get('internal_id', '—')}`\n"
            f"📱 Telegram ID: `{user_data['user_id']}`\n"
            f"📛 Имя: {user_data.get('first_name', '—')}\n"
            f"🔹 Username: @{user_data.get('username', '—') if user_data.get('username') else '—'}\n"
            f"📅 Первое появление: {user_data.get('first_seen', '—')}\n"
            f"🕒 Последняя активность: {user_data.get('last_active', '—')}")
    await message.answer(info, parse_mode="Markdown", reply_markup=get_admin_keyboard())
    await state.clear()

@router.message(SearchStates.waiting_query, Command("cancel"))
async def cancel_search(message: Message, state: FSMContext) -> None:
    await message.answer("❌ Поиск отменён", reply_markup=get_admin_keyboard())
    await state.clear()

@router.callback_query(F.data == "ad_settings")
async def ad_settings_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    status = "🟢 ВКЛЮЧЕНА" if ad_enabled else "🔴 ВЫКЛЮЧЕНА"
    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    ad_info = (f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
               f"Статус: {status}\n"
               f"Позиция: {position_text}\n"
               f"Задержка: {ad_delay} сек.\n")
    if ad_photo_id:
        ad_info += "✅ Фото установлено\n"
        if ad_caption:
            ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"
    else:
        ad_info += "❌ Фото не установлено\n"
    await callback.message.edit_text(ad_info, reply_markup=get_ad_settings_keyboard())

@router.callback_query(F.data == "set_ad_photo")
async def set_ad_photo_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "📸 Отправьте фото для рекламы при /start.\n\n✅ Добавьте подпись к фото!\n❌ Для отмены отправьте /cancel",
        reply_markup=None
    )
    await state.set_state(AdStates.waiting_photo)

@router.message(AdStates.waiting_photo, F.photo)
async def process_ad_photo(message: Message, state: FSMContext) -> None:
    global ad_photo_id, ad_caption
    if not message.caption:
        await message.answer("❌ Добавьте подпись к фото!")
        return
    ad_photo_id = message.photo[-1].file_id
    ad_caption = message.caption
    await message.answer(
        f"✅ Фото для рекламы установлено!\n\nПодпись: {message.caption}\n\nТеперь можете настроить другие параметры.",
        reply_markup=get_ad_settings_keyboard()
    )
    await state.clear()

@router.message(AdStates.waiting_photo, Command("cancel"))
async def cancel_ad_photo(message: Message, state: FSMContext) -> None:
    await message.answer("❌ Установка рекламы отменена", reply_markup=get_ad_settings_keyboard())
    await state.clear()

@router.callback_query(F.data == "set_ad_delay")
async def set_ad_delay_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "⏱️ Введите задержку перед рекламой в СЕКУНДАХ (0-60):\n\nПример: 0 - без задержки\nПример: 3 - через 3 секунды\n❌ Для отмены отправьте /cancel",
        reply_markup=None
    )
    await state.set_state(AdStates.waiting_delay)

@router.message(AdStates.waiting_delay, F.text)
async def process_ad_delay(message: Message, state: FSMContext) -> None:
    global ad_delay
    try:
        delay = int(message.text)
        if delay < 0 or delay > 60:
            await message.answer("❌ Задержка должна быть от 0 до 60 секунд")
            return
        ad_delay = delay
        await message.answer(f"✅ Задержка установлена: {delay} секунд(ы)", reply_markup=get_ad_settings_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите ЧИСЛО (например: 0, 3, 5)")

@router.message(AdStates.waiting_delay, Command("cancel"))
async def cancel_ad_delay(message: Message, state: FSMContext) -> None:
    await message.answer("❌ Настройка задержки отменена", reply_markup=get_ad_settings_keyboard())
    await state.clear()

@router.callback_query(F.data == "toggle_ad_position")
async def toggle_ad_position_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    global ad_position
    ad_position = "after" if ad_position == "before" else "before"
    await callback.answer(f"✅ Реклама будет {'ДО' if ad_position == 'before' else 'ПОСЛЕ'} меню")
    await ad_settings_callback(callback)

@router.callback_query(F.data == "test_ad")
async def test_ad_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    if not ad_photo_id or not ad_caption:
        await callback.answer("❌ Сначала установите фото для рекламы!", show_alert=True)
        return
    await callback.answer("👁️ Отправляю тестовое рекламное сообщение...")
    if await send_ad(callback.from_user.id):
        await callback.message.edit_text("✅ Тестовая реклама отправлена!", reply_markup=get_ad_settings_keyboard())
    else:
        await callback.message.edit_text("❌ Ошибка отправки тестовой рекламы!", reply_markup=get_ad_settings_keyboard())

@router.callback_query(F.data == "enable_ad")
async def enable_ad_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    global ad_enabled
    if not ad_photo_id:
        await callback.answer("❌ Сначала установите фото для рекламы!", show_alert=True)
        return
    ad_enabled = True
    await callback.answer("✅ Реклама при /start ВКЛЮЧЕНА!", show_alert=True)
    await ad_settings_callback(callback)

@router.callback_query(F.data == "disable_ad")
async def disable_ad_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    global ad_enabled
    ad_enabled = False
    await callback.answer("⏸️ Реклама при /start ВЫКЛЮЧЕНА!", show_alert=True)
    await ad_settings_callback(callback)

@router.callback_query(F.data == "delete_ad")
async def delete_ad_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    global ad_photo_id, ad_caption, ad_enabled
    ad_photo_id = None
    ad_caption = None
    ad_enabled = False
    await callback.answer("🗑️ Реклама удалена!", show_alert=True)
    await ad_settings_callback(callback)

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "👑 Добро пожаловать в админ панель!\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )

# ===== РАССЫЛКА =====
@router.callback_query(F.data == "newsletter_photo")
async def newsletter_photo_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "📸 Отправьте фото для рассылки.\n\n✅ Добавьте подпись к фото!\n❌ Для отмены отправьте /cancel",
        reply_markup=None
    )
    await state.set_state(NewsletterStates.waiting_photo)

@router.message(NewsletterStates.waiting_photo, F.photo)
async def process_newsletter_photo(message: Message, state: FSMContext) -> None:
    global newsletter_photo_id, newsletter_caption
    if not message.caption:
        await message.answer("❌ Добавьте подпись к фото!")
        return
    newsletter_photo_id = message.photo[-1].file_id
    newsletter_caption = message.caption
    users = await get_users()
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, отправить ВСЕМ", callback_data="confirm_photo")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_newsletter")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        f"📸 Начинаем рассылку?\n\nПодпись: {message.caption}\nВсего пользователей: {len(users)}\n\n⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
        reply_markup=markup
    )
    await state.clear()

@router.message(NewsletterStates.waiting_photo, Command("cancel"))
async def cancel_newsletter_photo(message: Message, state: FSMContext) -> None:
    await message.answer("❌ Рассылка отменена", reply_markup=get_admin_keyboard())
    await state.clear()

@router.callback_query(F.data == "newsletter_text")
async def newsletter_text_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "📝 Отправьте текст для рассылки.\n\n❌ Для отмены отправьте /cancel",
        reply_markup=None
    )
    await state.set_state(NewsletterStates.waiting_text)

@router.message(NewsletterStates.waiting_text, F.text)
async def process_newsletter_text(message: Message, state: FSMContext) -> None:
    global newsletter_text
    newsletter_text = message.text
    users = await get_users()
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, отправить ВСЕМ", callback_data="confirm_text")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_newsletter")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        f"📝 Начинаем рассылку?\n\nТекст: {message.text}\nВсего пользователей: {len(users)}\n\n⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
        reply_markup=markup
    )
    await state.clear()

@router.message(NewsletterStates.waiting_text, Command("cancel"))
async def cancel_newsletter_text(message: Message, state: FSMContext) -> None:
    await message.answer("❌ Рассылка отменена", reply_markup=get_admin_keyboard())
    await state.clear()

@router.callback_query(F.data == "confirm_photo")
async def confirm_photo_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        return
    await callback.answer()
    await callback.message.edit_text("⏳ Идет рассылка ВСЕМ пользователям...\nЭто может занять некоторое время")
    users = await get_users()
    sent = failed = blocked = 0
    total = len(users)
    for i, user_id in enumerate(users, 1):
        try:
            await bot.send_photo(int(user_id), photo=newsletter_photo_id, caption=newsletter_caption, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1
            if "blocked" in str(e).lower():
                blocked += 1
        if i % 20 == 0:
            await asyncio.sleep(1)
    await callback.message.edit_text(
        f"✅ Рассылка завершена!\n\n📊 Статистика:\n📸 Отправлено: {sent}\n❌ Не доставлено: {failed}\n🚫 Заблокировали бота: {blocked}\n👥 Всего в базе: {total}",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "confirm_text")
async def confirm_text_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        return
    await callback.answer()
    await callback.message.edit_text("⏳ Идет рассылка ВСЕМ пользователям...\nЭто может занять некоторое время")
    users = await get_users()
    sent = failed = blocked = 0
    total = len(users)
    for i, user_id in enumerate(users, 1):
        try:
            await bot.send_message(int(user_id), newsletter_text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1
            if "blocked" in str(e).lower():
                blocked += 1
        if i % 20 == 0:
            await asyncio.sleep(1)
    await callback.message.edit_text(
        f"✅ Рассылка завершена!\n\n📊 Статистика:\n📝 Отправлено: {sent}\n❌ Не доставлено: {failed}\n🚫 Заблокировали бота: {blocked}\n👥 Всего в базе: {total}",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "cancel_newsletter")
async def cancel_newsletter_callback(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMINS:
        return
    await callback.answer()
    await callback.message.edit_text("❌ Рассылка отменена", reply_markup=get_admin_keyboard())


# ===== ГЛАВНАЯ ФУНКЦИЯ =====
async def main():
    dp.include_router(router)
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
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
