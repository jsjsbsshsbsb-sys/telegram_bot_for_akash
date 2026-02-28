import telebot
from telebot import types
import time
import os
import threading
from datetime import datetime, timedelta

TOKEN = "8564117995:AAEkciU1is19cCSwyz7UFZOktYKEXX2djiA"
bot = telebot.TeleBot(TOKEN)
ADMINS = [7041448219]

# Глобальные переменные для рассылки и рекламы
newsletter_photo_id = None
newsletter_caption = None
newsletter_text = None

# Переменные для рекламы при /start
ad_photo_id = None
ad_caption = None
ad_enabled = False  # Включена ли реклама
ad_delay = 0  # Задержка перед рекламой (в секундах)
ad_position = "after"  # "before" - до меню, "after" - после меню


# ===== ПРОВЕРКА ПОДПИСКИ =====
def check_subscription(user_id):
    CHANNEL_USERNAME = "@nastroytut"
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"SUB CHECK ERROR: {e}")
        return False


# ===== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ =====
def save_user(user_id):
    try:
        with open("users.txt", "a+") as f:
            f.seek(0)
            users = f.read().splitlines()
            if str(user_id) not in users:
                f.write(str(user_id) + "\n")
                print(f"✅ Новый пользователь: {user_id}")
    except Exception as e:
        print(f"SAVE USER ERROR: {e}")


def get_users():
    try:
        with open("users.txt", "r") as f:
            users = f.read().splitlines()
            print(f"📊 Всего пользователей в базе: {len(users)}")
            return users
    except:
        print("❌ Файл users.txt не найден, создаю новый")
        return []


# ===== ФУНКЦИЯ ОТПРАВКИ РЕКЛАМЫ =====
def send_ad(user_id):
    if ad_enabled and ad_photo_id and ad_caption:
        try:
            bot.send_photo(user_id, ad_photo_id, caption=ad_caption, parse_mode="html")
            print(f"✅ Реклама отправлена пользователю {user_id}")
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки рекламы пользователю {user_id}: {e}")
            return False
    return False


# ===== ГЛАВНОЕ МЕНЮ =====
def send_main_menu(message):
    markup_menu_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
    iphone_btn = types.KeyboardButton("🍎IPhone🍎")
    android_btn = types.KeyboardButton("🤖Android🤖")
    coders_btn = types.KeyboardButton("ℹ️Разработчикиℹ️")
    cooperation_btn = types.KeyboardButton("🤳Сотрудничество🤳")
    markup_menu_buttons.add(iphone_btn, android_btn)
    markup_menu_buttons.add(coders_btn, cooperation_btn)

    bot.send_message(
        message.chat.id,
        "<blockquote>✅ Добро пожаловать в бота для Настроек FreeFire!\n\nВыберите своё устройство! 👇</blockquote>",
        reply_markup=markup_menu_buttons, parse_mode="html"
    )


# ===== ФУНКЦИЯ ВОЗВРАТА =====
def go_back_func(message):
    markup_menu_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
    iphone_btn = types.KeyboardButton("🍎IPhone🍎")
    android_btn = types.KeyboardButton("🤖Android🤖")
    coders_btn = types.KeyboardButton("ℹ️Разработчикиℹ️")
    cooperation_btn = types.KeyboardButton("🤳Сотрудничество🤳")
    markup_menu_buttons.add(iphone_btn, android_btn)
    markup_menu_buttons.add(coders_btn, cooperation_btn)

    try:
        if os.path.exists("menu_logo.jpg"):
            with open("menu_logo.jpg", "rb") as menu_logo:
                bot.send_photo(message.chat.id, menu_logo,
                               caption="<blockquote>📋Вы вернулись в меню!📋</blockquote>",
                               reply_markup=markup_menu_buttons, parse_mode="html")
        else:
            bot.send_message(message.chat.id, "📋Вы вернулись в меню!📋",
                             reply_markup=markup_menu_buttons)
    except:
        bot.send_message(message.chat.id, "📋Вы вернулись в меню!📋",
                         reply_markup=markup_menu_buttons)


# ===== СТАРТ =====
@bot.message_handler(commands=["start"])
def private_hendler(message):
    save_user(message.chat.id)

    if not check_subscription(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        subscribe_btn = types.InlineKeyboardButton("📢 Подписаться", url="https://t.me/nastroytut")
        check_sub_btn = types.InlineKeyboardButton("🟢 Проверить", callback_data="check_sub")
        markup.add(subscribe_btn)
        markup.add(check_sub_btn)
        bot.send_message(
            message.chat.id,
            "Вы не подписаны на наш телеграмм канал!\nБот заработает после подписки!",
            reply_markup=markup
        )
        return

    # Отправка рекламы в зависимости от настроек
    if ad_enabled and ad_photo_id and ad_caption:
        if ad_position == "before":
            # Реклама ДО меню
            send_ad(message.chat.id)
            if ad_delay > 0:
                time.sleep(ad_delay)
            send_main_menu(message)
        else:
            # Реклама ПОСЛЕ меню
            send_main_menu(message)
            if ad_delay > 0:
                time.sleep(ad_delay)
            send_ad(message.chat.id)
    else:
        send_main_menu(message)


# ===== ПРОВЕРКА ПОДПИСКИ =====
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_button(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Вы подписаны! Можно пользоваться ботом.", show_alert=True)
        send_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны на канал!", show_alert=True)


# ===== АДМИН ПАНЕЛЬ =====
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора!")
        return

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📢 Рассылка (фото)", callback_data="newsletter_photo")
    btn2 = types.InlineKeyboardButton("📢 Рассылка (текст)", callback_data="newsletter_text")
    btn3 = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    btn4 = types.InlineKeyboardButton("👥 Список пользователей", callback_data="users_list")
    btn5 = types.InlineKeyboardButton("🔄 НАСТРОЙКА РЕКЛАМЫ", callback_data="ad_settings")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)

    bot.send_message(message.chat.id,
                     "👑 Добро пожаловать в админ панель!\nВыберите действие:",
                     reply_markup=markup)


# ===== НАСТРОЙКА РЕКЛАМЫ ПРИ /START =====
@bot.callback_query_handler(func=lambda call: call.data == "ad_settings")
def ad_settings_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📸 Установить фото", callback_data="set_ad_photo")
    btn2 = types.InlineKeyboardButton("⏱️ Настроить задержку", callback_data="set_ad_delay")
    btn3 = types.InlineKeyboardButton("📌 Позиция: " + ("ДО меню" if ad_position == "before" else "ПОСЛЕ меню"),
                                      callback_data="toggle_ad_position")

    if ad_enabled:
        btn4 = types.InlineKeyboardButton("⏸️ Выключить рекламу", callback_data="disable_ad")
    else:
        btn4 = types.InlineKeyboardButton("▶️ Включить рекламу", callback_data="enable_ad")

    btn5 = types.InlineKeyboardButton("👁️ Тест рекламы", callback_data="test_ad")
    btn6 = types.InlineKeyboardButton("🗑️ Удалить рекламу", callback_data="delete_ad")
    btn7 = types.InlineKeyboardButton("🔙 Назад в админку", callback_data="back_to_admin")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)
    markup.add(btn6)
    markup.add(btn7)

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

    bot.send_message(call.message.chat.id, ad_info, reply_markup=markup)


# ===== УСТАНОВКА ФОТО ДЛЯ РЕКЛАМЫ =====
@bot.callback_query_handler(func=lambda call: call.data == "set_ad_photo")
def set_ad_photo_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
                           "📸 Отправьте фото для рекламы при /start.\n\n"
                           "✅ Добавьте подпись к фото!\n"
                           "❌ Для отмены отправьте /cancel")
    bot.register_next_step_handler(msg, process_ad_photo)


def process_ad_photo(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ Установка рекламы отменена")
        return

    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фото! Отправьте фото с подписью.")
        return

    if not message.caption:
        bot.send_message(message.chat.id, "❌ Добавьте подпись к фото!")
        return

    global ad_photo_id, ad_caption
    ad_photo_id = message.photo[-1].file_id
    ad_caption = message.caption

    bot.send_message(message.chat.id,
                     f"✅ Фото для рекламы установлено!\n\n"
                     f"Подпись: {message.caption}\n\n"
                     f"Теперь можете настроить другие параметры.")


# ===== НАСТРОЙКА ЗАДЕРЖКИ =====
@bot.callback_query_handler(func=lambda call: call.data == "set_ad_delay")
def set_ad_delay_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
                           "⏱️ Введите задержку перед рекламой в СЕКУНДАХ (0-60):\n\n"
                           "Пример: 0 - без задержки\n"
                           "Пример: 3 - через 3 секунды\n"
                           "❌ Для отмены отправьте /cancel")
    bot.register_next_step_handler(msg, process_ad_delay)


def process_ad_delay(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ Настройка задержки отменена")
        return

    try:
        delay = int(message.text)
        if delay < 0 or delay > 60:
            bot.send_message(message.chat.id, "❌ Задержка должна быть от 0 до 60 секунд")
            return

        global ad_delay
        ad_delay = delay

        bot.send_message(message.chat.id,
                         f"✅ Задержка установлена: {delay} секунд(ы)")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите ЧИСЛО (например: 0, 3, 5)")


# ===== ПЕРЕКЛЮЧЕНИЕ ПОЗИЦИИ РЕКЛАМЫ =====
@bot.callback_query_handler(func=lambda call: call.data == "toggle_ad_position")
def toggle_ad_position_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    global ad_position
    ad_position = "after" if ad_position == "before" else "before"

    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"
    bot.answer_callback_query(call.id, f"✅ Реклама будет {position_text.lower()}")

    # Обновляем сообщение с настройками
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📸 Установить фото", callback_data="set_ad_photo")
    btn2 = types.InlineKeyboardButton("⏱️ Настроить задержку", callback_data="set_ad_delay")
    btn3 = types.InlineKeyboardButton("📌 Позиция: " + ("ДО меню" if ad_position == "before" else "ПОСЛЕ меню"),
                                      callback_data="toggle_ad_position")

    if ad_enabled:
        btn4 = types.InlineKeyboardButton("⏸️ Выключить рекламу", callback_data="disable_ad")
    else:
        btn4 = types.InlineKeyboardButton("▶️ Включить рекламу", callback_data="enable_ad")

    btn5 = types.InlineKeyboardButton("👁️ Тест рекламы", callback_data="test_ad")
    btn6 = types.InlineKeyboardButton("🗑️ Удалить рекламу", callback_data="delete_ad")
    btn7 = types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)
    markup.add(btn6)
    markup.add(btn7)

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

    bot.edit_message_text(ad_info, call.message.chat.id, call.message.message_id, reply_markup=markup)


# ===== ТЕСТ РЕКЛАМЫ =====
@bot.callback_query_handler(func=lambda call: call.data == "test_ad")
def test_ad_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    if not ad_photo_id or not ad_caption:
        bot.answer_callback_query(call.id, "❌ Сначала установите фото для рекламы!", show_alert=True)
        return

    bot.answer_callback_query(call.id, "👁️ Отправляю тестовое рекламное сообщение...")

    if send_ad(call.message.chat.id):
        bot.send_message(call.message.chat.id, "✅ Тестовая реклама отправлена!")
    else:
        bot.send_message(call.message.chat.id, "❌ Ошибка отправки тестовой рекламы!")


# ===== ВКЛЮЧЕНИЕ РЕКЛАМЫ =====
@bot.callback_query_handler(func=lambda call: call.data == "enable_ad")
def enable_ad_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    global ad_enabled

    if not ad_photo_id:
        bot.answer_callback_query(call.id, "❌ Сначала установите фото для рекламы!", show_alert=True)
        return

    ad_enabled = True
    bot.answer_callback_query(call.id, "✅ Реклама при /start ВКЛЮЧЕНА!", show_alert=True)

    # Обновляем сообщение с настройками
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📸 Установить фото", callback_data="set_ad_photo")
    btn2 = types.InlineKeyboardButton("⏱️ Настроить задержку", callback_data="set_ad_delay")
    btn3 = types.InlineKeyboardButton("📌 Позиция: " + ("ДО меню" if ad_position == "before" else "ПОСЛЕ меню"),
                                      callback_data="toggle_ad_position")
    btn4 = types.InlineKeyboardButton("⏸️ Выключить рекламу", callback_data="disable_ad")
    btn5 = types.InlineKeyboardButton("👁️ Тест рекламы", callback_data="test_ad")
    btn6 = types.InlineKeyboardButton("🗑️ Удалить рекламу", callback_data="delete_ad")
    btn7 = types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)
    markup.add(btn6)
    markup.add(btn7)

    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"

    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: 🟢 ВКЛЮЧЕНА\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    ad_info += f"✅ Фото установлено\n"
    ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"

    bot.edit_message_text(ad_info, call.message.chat.id, call.message.message_id, reply_markup=markup)


# ===== ВЫКЛЮЧЕНИЕ РЕКЛАМЫ =====
@bot.callback_query_handler(func=lambda call: call.data == "disable_ad")
def disable_ad_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    global ad_enabled

    ad_enabled = False
    bot.answer_callback_query(call.id, "⏸️ Реклама при /start ВЫКЛЮЧЕНА!", show_alert=True)

    # Обновляем сообщение с настройками
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📸 Установить фото", callback_data="set_ad_photo")
    btn2 = types.InlineKeyboardButton("⏱️ Настроить задержку", callback_data="set_ad_delay")
    btn3 = types.InlineKeyboardButton("📌 Позиция: " + ("ДО меню" if ad_position == "before" else "ПОСЛЕ меню"),
                                      callback_data="toggle_ad_position")
    btn4 = types.InlineKeyboardButton("▶️ Включить рекламу", callback_data="enable_ad")
    btn5 = types.InlineKeyboardButton("👁️ Тест рекламы", callback_data="test_ad")
    btn6 = types.InlineKeyboardButton("🗑️ Удалить рекламу", callback_data="delete_ad")
    btn7 = types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)
    markup.add(btn6)
    markup.add(btn7)

    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"

    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: 🔴 ВЫКЛЮЧЕНА\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    ad_info += f"✅ Фото установлено\n"
    ad_info += f"📝 Подпись: {ad_caption[:50]}...\n"

    bot.edit_message_text(ad_info, call.message.chat.id, call.message.message_id, reply_markup=markup)


# ===== УДАЛЕНИЕ РЕКЛАМЫ =====
@bot.callback_query_handler(func=lambda call: call.data == "delete_ad")
def delete_ad_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    global ad_photo_id, ad_caption, ad_enabled

    ad_photo_id = None
    ad_caption = None
    ad_enabled = False

    bot.answer_callback_query(call.id, "🗑️ Реклама удалена!", show_alert=True)

    # Обновляем сообщение с настройками
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📸 Установить фото", callback_data="set_ad_photo")
    btn2 = types.InlineKeyboardButton("⏱️ Настроить задержку", callback_data="set_ad_delay")
    btn3 = types.InlineKeyboardButton("📌 Позиция: " + ("ДО меню" if ad_position == "before" else "ПОСЛЕ меню"),
                                      callback_data="toggle_ad_position")
    btn7 = types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn7)

    position_text = "ДО меню" if ad_position == "before" else "ПОСЛЕ меню"

    ad_info = f"📢 НАСТРОЙКИ РЕКЛАМЫ ПРИ /START\n\n"
    ad_info += f"Статус: 🔴 ВЫКЛЮЧЕНА\n"
    ad_info += f"Позиция: {position_text}\n"
    ad_info += f"Задержка: {ad_delay} сек.\n"
    ad_info += f"❌ Фото не установлено\n"

    bot.edit_message_text(ad_info, call.message.chat.id, call.message.message_id, reply_markup=markup)


# ===== НАЗАД В АДМИНКУ =====
@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def back_to_admin_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📢 Рассылка (фото)", callback_data="newsletter_photo")
    btn2 = types.InlineKeyboardButton("📢 Рассылка (текст)", callback_data="newsletter_text")
    btn3 = types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
    btn4 = types.InlineKeyboardButton("👥 Список пользователей", callback_data="users_list")
    btn5 = types.InlineKeyboardButton("🔄 НАСТРОЙКА РЕКЛАМЫ", callback_data="ad_settings")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)

    bot.send_message(call.message.chat.id,
                     "👑 Добро пожаловать в админ панель!\nВыберите действие:",
                     reply_markup=markup)


# ===== СТАТИСТИКА =====
@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    users = get_users()

    ad_status = "Включена" if ad_enabled else "Выключена"
    position_text = "До меню" if ad_position == "before" else "После меню"

    bot.send_message(call.message.chat.id,
                     f"📊 СТАТИСТИКА БОТА:\n\n"
                     f"👥 Всего пользователей: {len(users)}\n"
                     f"🆔 Ваш ID: {call.from_user.id}\n\n"
                     f"📢 РЕКЛАМА ПРИ /START:\n"
                     f"Статус: {ad_status}\n"
                     f"Позиция: {position_text}\n"
                     f"Задержка: {ad_delay} сек.\n"
                     f"Фото: {'✅' if ad_photo_id else '❌'}")


# ===== СПИСОК ПОЛЬЗОВАТЕЛЕЙ =====
@bot.callback_query_handler(func=lambda call: call.data == "users_list")
def users_list_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    users = get_users()

    if not users:
        bot.send_message(call.message.chat.id, "📭 Список пользователей пуст")
        return

    # Отправляем список частями по 20 пользователей
    text = "👥 Список пользователей:\n\n"
    for i, user_id in enumerate(users, 1):
        text += f"{i}. {user_id}\n"
        if i % 20 == 0:
            bot.send_message(call.message.chat.id, text)
            text = ""

    if text:
        bot.send_message(call.message.chat.id, text)


# ===== РАССЫЛКА С ФОТО =====
@bot.callback_query_handler(func=lambda call: call.data == "newsletter_photo")
def newsletter_photo_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
                           "📸 Отправьте фото для рассылки.\n\n"
                           "✅ Добавьте подпись к фото!\n"
                           "❌ Для отмены отправьте /cancel")
    bot.register_next_step_handler(msg, process_photo_newsletter)


def process_photo_newsletter(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ Рассылка отменена")
        return

    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фото! Отправьте фото с подписью.")
        return

    if not message.caption:
        bot.send_message(message.chat.id, "❌ Добавьте подпись к фото!")
        return

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("✅ Да, отправить ВСЕМ", callback_data="confirm_photo")
    btn2 = types.InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel")
    markup.add(btn1, btn2)

    global newsletter_photo_id, newsletter_caption
    newsletter_photo_id = message.photo[-1].file_id
    newsletter_caption = message.caption

    users = get_users()
    bot.send_message(message.chat.id,
                     f"📸 Начинаем рассылку?\n\n"
                     f"Подпись: {message.caption}\n"
                     f"Всего пользователей: {len(users)}\n\n"
                     f"⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
                     reply_markup=markup)


# ===== РАССЫЛКА С ТЕКСТОМ =====
@bot.callback_query_handler(func=lambda call: call.data == "newsletter_text")
def newsletter_text_handler(call):
    if call.message.chat.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
                           "📝 Отправьте текст для рассылки.\n\n"
                           "❌ Для отмены отправьте /cancel")
    bot.register_next_step_handler(msg, process_text_newsletter)


def process_text_newsletter(message):
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ Рассылка отменена")
        return

    if not message.text:
        bot.send_message(message.chat.id, "❌ Отправьте текст!")
        return

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("✅ Да, отправить ВСЕМ", callback_data="confirm_text")
    btn2 = types.InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel")
    markup.add(btn1, btn2)

    global newsletter_text
    newsletter_text = message.text

    users = get_users()
    bot.send_message(message.chat.id,
                     f"📝 Начинаем рассылку?\n\n"
                     f"Текст: {message.text}\n"
                     f"Всего пользователей: {len(users)}\n\n"
                     f"⚠️ Рассылка будет отправлена ВСЕМ пользователям!",
                     reply_markup=markup)


# ===== ПОДТВЕРЖДЕНИЕ РАССЫЛКИ С ФОТО =====
@bot.callback_query_handler(func=lambda call: call.data == "confirm_photo")
def confirm_photo_handler(call):
    if call.message.chat.id not in ADMINS:
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_text("⏳ Идет рассылка ВСЕМ пользователям...\nЭто может занять некоторое время",
                          call.message.chat.id, call.message.message_id)

    users = get_users()
    sent = 0
    failed = 0
    blocked = 0
    total = len(users)

    for i, user_id in enumerate(users, 1):
        try:
            bot.send_photo(user_id, newsletter_photo_id, caption=newsletter_caption, parse_mode="html")
            sent += 1
            print(f"✅ [{i}/{total}] Отправлено пользователю {user_id}")
        except Exception as e:
            failed += 1
            error_text = str(e).lower()
            if "blocked" in error_text:
                blocked += 1
                print(f"❌ [{i}/{total}] Пользователь {user_id} заблокировал бота")
            elif "chat not found" in error_text:
                print(f"❌ [{i}/{total}] Чат с {user_id} не найден")
            else:
                print(f"❌ [{i}/{total}] Ошибка отправки {user_id}: {e}")

    bot.send_message(call.message.chat.id,
                     f"✅ Рассылка завершена!\n\n"
                     f"📊 Статистика:\n"
                     f"📸 Отправлено: {sent}\n"
                     f"❌ Не доставлено: {failed}\n"
                     f"🚫 Заблокировали бота: {blocked}\n"
                     f"👥 Всего в базе: {total}")


# ===== ПОДТВЕРЖДЕНИЕ РАССЫЛКИ С ТЕКСТОМ =====
@bot.callback_query_handler(func=lambda call: call.data == "confirm_text")
def confirm_text_handler(call):
    if call.message.chat.id not in ADMINS:
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_text("⏳ Идет рассылка ВСЕМ пользователям...\nЭто может занять некоторое время",
                          call.message.chat.id, call.message.message_id)

    users = get_users()
    sent = 0
    failed = 0
    blocked = 0
    total = len(users)

    for i, user_id in enumerate(users, 1):
        try:
            bot.send_message(user_id, newsletter_text, parse_mode="html")
            sent += 1
            print(f"✅ [{i}/{total}] Отправлено пользователю {user_id}")
        except Exception as e:
            failed += 1
            error_text = str(e).lower()
            if "blocked" in error_text:
                blocked += 1
                print(f"❌ [{i}/{total}] Пользователь {user_id} заблокировал бота")
            elif "chat not found" in error_text:
                print(f"❌ [{i}/{total}] Чат с {user_id} не найден")
            else:
                print(f"❌ [{i}/{total}] Ошибка отправки {user_id}: {e}")

    bot.send_message(call.message.chat.id,
                     f"✅ Рассылка завершена!\n\n"
                     f"📊 Статистика:\n"
                     f"📝 Отправлено: {sent}\n"
                     f"❌ Не доставлено: {failed}\n"
                     f"🚫 Заблокировали бота: {blocked}\n"
                     f"👥 Всего в базе: {total}")


# ===== ОТМЕНА =====
@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_handler(call):
    if call.message.chat.id not in ADMINS:
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_text("❌ Рассылка отменена", call.message.chat.id, call.message.message_id)


# ===== IPHONE 7 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_7")
def iphone_7_handler(call):
    bot.answer_callback_query(call.id)
    iph_7_markup = types.InlineKeyboardMarkup()
    iphone_7_base_btn = types.InlineKeyboardButton("IPhone 7", callback_data="iphone_7_base")
    iphone_7_plus_btn = types.InlineKeyboardButton("IPhone 7 Plus", callback_data="iphone_7_plus")
    iph_7_markup.add(iphone_7_base_btn)
    iph_7_markup.add(iphone_7_plus_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 7👇", reply_markup=iph_7_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_7_base")
def iphone_7_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 7 Base\n<blockquote>DPI 31\nОбзор 170\nКоллиматор 198\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 44</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_7_plus")
def iphone_7_plus_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 7 Plus\n<blockquote>DPI 54\nОбзор 178\nКоллиматор 152\n2x 129\n4х 121\nСнайп прицел 137\nСвободный обзор 76\nКнопка огня: 46</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 8 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_8")
def iphone_8_handler(call):
    bot.answer_callback_query(call.id)
    iph_8_markup = types.InlineKeyboardMarkup()
    iphone_8_base_btn = types.InlineKeyboardButton("IPhone 8", callback_data="iphone_8_base")
    iphone_8_plus_btn = types.InlineKeyboardButton("IPhone 8 Plus", callback_data="iphone_8_plus")
    iph_8_markup.add(iphone_8_base_btn)
    iph_8_markup.add(iphone_8_plus_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 8👇", reply_markup=iph_8_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_8_base")
def iphone_8_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 8 Base\n<blockquote>Обзор: 167\nКоллиматор: 185\n2x Прицел: 181\n4x Прицел: 173\nКнопка: 50%\nDPI: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_8_plus")
def iphone_8_plus_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 8 Plus\n<blockquote>DPI 31\nОбзор 100\nКоллиматор 187\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE X =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_10")
def iphone_10_handler(call):
    bot.answer_callback_query(call.id)
    iph_10_markup = types.InlineKeyboardMarkup()
    iphone_10_base_btn = types.InlineKeyboardButton("IPhone X", callback_data="iphone_10_base")
    iphone_10_s_btn = types.InlineKeyboardButton("IPhone XS", callback_data="iphone_10_s")
    iphone_10_x_r_btn = types.InlineKeyboardButton("IPhone XR", callback_data="iphone_x_r")
    iphone_10_s_max_btn = types.InlineKeyboardButton("IPhone XS Max", callback_data="iphone_10_s_max")
    iph_10_markup.add(iphone_10_base_btn)
    iph_10_markup.add(iphone_10_x_r_btn)
    iph_10_markup.add(iphone_10_s_btn)
    iph_10_markup.add(iphone_10_s_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone X👇", reply_markup=iph_10_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_x_r")
def iphone_x_r_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone XR\n<blockquote>Dpi 120\nобзор 129\nКоллиматор 99\n2x 156\n4x 164\nСнайп прицел 100\nСвободный обзор 100\nКнопка огня 36</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_10_base")
def iphone_10_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone X Base\n<blockquote>Dpi 31\nОбзор 177\nКоллиматор 195\n2x 198\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 49</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_10_s")
def iphone_10_s_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone XS\n<blockquote>Dpi 49\nОбзор 100\nКоллиматор 120\n2x 100\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_10_s_max")
def iphone_10_s_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone XS Max\n<blockquote>Обзор: 175\nКоллиматор: 185\n2x Прицел: 195\n4x Прицел: 173\nКнопка: 53%\nDPI: 31</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 11 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_11")
def iphone_11_handler(call):
    bot.answer_callback_query(call.id)
    iph_11_markup = types.InlineKeyboardMarkup()
    iphone_11_base_btn = types.InlineKeyboardButton("IPhone 11", callback_data="iphone_11_base")
    iphone_11_pro_btn = types.InlineKeyboardButton("IPhone 11 Pro", callback_data="iphone_11_pro")
    iphone_11_pro_max_btn = types.InlineKeyboardButton("IPhone 11 Pro Max", callback_data="iphone_11_pro_max")
    iph_11_markup.add(iphone_11_base_btn)
    iph_11_markup.add(iphone_11_pro_btn)
    iph_11_markup.add(iphone_11_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 11👇", reply_markup=iph_11_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_11_base")
def iphone_11_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 11\n<blockquote>Обзор 149\nКоллиматор 150\n2х 200\n4х 180\nСнайп прицел 200\nСвободный обзор 200\nКнопка огня 39\nDPI: 31</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_11_pro")
def iphone_11_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 11 Pro\n<blockquote>обзор:170\nколлиматор:165\n2х прицел:155\n4х прицел:135\nснайперский прицел:110\nСвободная камера:130\n58-62 кнопка огня</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_11_pro_max")
def iphone_11_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки на IPhone 11 Pro Max\n<blockquote>Обзор 108\nКоллиматор 94\n2x 125\n4x 124\nСнайп прицел 66\nСвободный обзор 41\nDpi: 100\nКнопка огня: 45</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 12 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_12")
def iphone_12_handler(call):
    bot.answer_callback_query(call.id)
    iph_12_markup = types.InlineKeyboardMarkup()
    iphone_12_base_btn = types.InlineKeyboardButton("IPhone 12", callback_data="iphone_12_base")
    iphone_12_mini_btn = types.InlineKeyboardButton("IPhone 12 Mini", callback_data="iphone_12_mini")
    iphone_12_pro_btn = types.InlineKeyboardButton("IPhone 12 Pro", callback_data="iphone_12_pro")
    iphone_12_pro_max_btn = types.InlineKeyboardButton("IPhone 12 Pro Max", callback_data="iphone_12_pro_max")
    iph_12_markup.add(iphone_12_base_btn)
    iph_12_markup.add(iphone_12_mini_btn)
    iph_12_markup.add(iphone_12_pro_btn)
    iph_12_markup.add(iphone_12_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 12👇", reply_markup=iph_12_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_12_base")
def iphone_12_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 12\n<blockquote>Обзор: 165\nКоллиматор: 158\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 50\nDpi: 33</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_12_mini")
def iphone_12_mini_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 12 Mini\n<blockquote>Обзор: 158\nКоллиматор: 150\n2x: 135\n4x: 115\nСнайп прицел: 95\nСвободный обзор: 105\nКнопка огня: 48\nDpi: 42</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_12_pro")
def iphone_12_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 12 Pro\n<blockquote>Обзор: 168\nКоллиматор: 160\n2x: 145\n4x: 125\nСнайп прицел: 100\nСвободный обзор: 112\nКнопка огня: 50\nDpi: 35</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_12_pro_max")
def iphone_12_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 12 Pro Max\n<blockquote>Обзор: 172\nКоллиматор: 165\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 52\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 13 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_13")
def iphone_13_handler(call):
    bot.answer_callback_query(call.id)
    iph_13_markup = types.InlineKeyboardMarkup()
    iphone_13_base_btn = types.InlineKeyboardButton("IPhone 13", callback_data="iphone_13_base")
    iphone_13_mini_btn = types.InlineKeyboardButton("IPhone 13 Mini", callback_data="iphone_13_mini")
    iphone_13_pro_btn = types.InlineKeyboardButton("IPhone 13 Pro", callback_data="iphone_13_pro")
    iphone_13_pro_max_btn = types.InlineKeyboardButton("IPhone 13 Pro Max", callback_data="iphone_13_pro_max")
    iph_13_markup.add(iphone_13_base_btn)
    iph_13_markup.add(iphone_13_mini_btn)
    iph_13_markup.add(iphone_13_pro_btn)
    iph_13_markup.add(iphone_13_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 13👇", reply_markup=iph_13_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_13_base")
def iphone_13_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 13\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 120\nКнопка огня: 50\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_13_mini")
def iphone_13_mini_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 13 Mini\n<blockquote>Обзор: 170\nКоллиматор: 162\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 48\nDpi: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_13_pro")
def iphone_13_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 13 Pro\n<blockquote>Обзор: 161\nКоллиматор: 168\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 50%\nDpi: 53</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_13_pro_max")
def iphone_13_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 13 Pro Max\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 118\nКнопка огня: 52\nДпиай: 37</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 14 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_14")
def iphone_14_handler(call):
    bot.answer_callback_query(call.id)
    iph_14_markup = types.InlineKeyboardMarkup()
    iphone_14_base_btn = types.InlineKeyboardButton("IPhone 14", callback_data="iphone_14_base")
    iphone_14_plus_btn = types.InlineKeyboardButton("IPhone 14 Plus", callback_data="iphone_14_plus")
    iphone_14_pro_btn = types.InlineKeyboardButton("IPhone 14 Pro", callback_data="iphone_14_pro")
    iphone_14_pro_max_btn = types.InlineKeyboardButton("IPhone 14 Pro Max", callback_data="iphone_14_pro_max")
    iph_14_markup.add(iphone_14_base_btn)
    iph_14_markup.add(iphone_14_plus_btn)
    iph_14_markup.add(iphone_14_pro_btn)
    iph_14_markup.add(iphone_14_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 14👇", reply_markup=iph_14_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_14_base")
def iphone_14_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 14\n<blockquote>Обзор: 180\nКоллиматор: 172\n2x: 152\n4x: 132\nСнайп прицел: 107\nСвободный обзор: 120\nКнопка огня: 50\nДпиай: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_14_plus")
def iphone_14_plus_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 14 Plus\n<blockquote>Обзор: 185\nКоллиматор: 176\n2x: 158\n4x: 138\nСнайп прицел: 110\nСвободный обзор: 125\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_14_pro")
def iphone_14_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 14 Pro\n<blockquote>Обзор: 187\nКоллиматор: 178\n2x: 160\n4x: 140\nСнайп прицел: 112\nСвободный обзор: 127\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_14_pro_max")
def iphone_14_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 14 Pro Max\n<blockquote>Обзор: 190\nКоллиматор: 182\n2x: 162\n4x: 142\nСнайп прицел: 115\nСвободный обзор: 130\nКнопка огня: 54\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 15 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_15")
def iphone_15_handler(call):
    bot.answer_callback_query(call.id)
    iph_15_markup = types.InlineKeyboardMarkup()
    iphone_15_base_btn = types.InlineKeyboardButton("IPhone 15", callback_data="iphone_15_base")
    iphone_15_plus_btn = types.InlineKeyboardButton("IPhone 15 Plus", callback_data="iphone_15_plus")
    iphone_15_pro_btn = types.InlineKeyboardButton("IPhone 15 Pro", callback_data="iphone_15_pro")
    iphone_15_pro_max_btn = types.InlineKeyboardButton("IPhone 15 Pro Max", callback_data="iphone_15_pro_max")
    iph_15_markup.add(iphone_15_base_btn)
    iph_15_markup.add(iphone_15_plus_btn)
    iph_15_markup.add(iphone_15_pro_btn)
    iph_15_markup.add(iphone_15_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 15👇", reply_markup=iph_15_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_15_base")
def iphone_15_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 15\n<blockquote>Обзор: 192\nКоллиматор: 184\n2x: 164\n4x: 144\nСнайп прицел: 117\nСвободный обзор: 132\nКнопка огня: 50\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_15_plus")
def iphone_15_plus_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 15 Plus\n<blockquote>Обзор: 195\nКоллиматор: 186\n2x: 166\n4x: 146\nСнайп прицел: 118\nСвободный обзор: 134\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_15_pro")
def iphone_15_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 15 Pro\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 120\nСвободный обзор: 136\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_15_pro_max")
def iphone_15_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 15 Pro Max\n<blockquote>Обзор: 200\nКоллиматор: 190\n2x: 170\n4x: 150\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 54\nDpi: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 16 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_16")
def iphone_16_handler(call):
    bot.answer_callback_query(call.id)
    iph_16_markup = types.InlineKeyboardMarkup()
    iphone_16_base_btn = types.InlineKeyboardButton("IPhone 16", callback_data="iphone_16_base")
    iphone_16_plus_btn = types.InlineKeyboardButton("IPhone 16 Plus", callback_data="iphone_16_plus")
    iphone_16_e_btn = types.InlineKeyboardButton("IPhone 16e", callback_data="iphone_16_e")
    iphone_16_pro_btn = types.InlineKeyboardButton("IPhone 16 Pro", callback_data="iphone_16_pro")
    iphone_16_pro_max_btn = types.InlineKeyboardButton("IPhone 16 Pro Max", callback_data="iphone_16_pro_max")
    iph_16_markup.add(iphone_16_base_btn)
    iph_16_markup.add(iphone_16_e_btn)
    iph_16_markup.add(iphone_16_plus_btn)
    iph_16_markup.add(iphone_16_pro_btn)
    iph_16_markup.add(iphone_16_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 16👇", reply_markup=iph_16_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_16_base")
def iphone_16_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 16\n<blockquote>Обзор: 195\nКоллиматор: 185\n2x: 165\n4x: 145\nСнайп прицел: 120\nСвободный обзор: 135\nКнопка огня: 50\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_16_e")
def iphone_16_e_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 16e\n<blockquote>Обзор: 138\nКоллиматор: 128\n2x: 123\n4x: 108\nСнайп прицел: 98\nСвободный обзор: 118\nКнопка огня: 50\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_16_plus")
def iphone_16_plus_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 16 Plus\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 52\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_16_pro")
def iphone_16_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 16 Pro\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 52\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_16_pro_max")
def iphone_16_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 16 Pro Max\n<blockquote>Обзор: 148\nКоллиматор: 138\n2x: 133\n4x: 118\nСнайп прицел: 108\nСвободный обзор: 128\nКнопка огня: 54\nДпиай: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== IPHONE 17 =====
@bot.callback_query_handler(func=lambda call: call.data == "iphone_17")
def iphone_17_handler(call):
    bot.answer_callback_query(call.id)
    iph_17_markup = types.InlineKeyboardMarkup()
    iphone_17_base_btn = types.InlineKeyboardButton("IPhone 17", callback_data="iphone_17_base")
    iphone_17_air_btn = types.InlineKeyboardButton("IPhone 17 Air", callback_data="iphone_17_air")
    iphone_17_pro_btn = types.InlineKeyboardButton("IPhone 17 Pro", callback_data="iphone_17_pro")
    iphone_17_pro_max_btn = types.InlineKeyboardButton("IPhone 17 Pro Max", callback_data="iphone_17_pro_max")
    iph_17_markup.add(iphone_17_base_btn)
    iph_17_markup.add(iphone_17_air_btn)
    iph_17_markup.add(iphone_17_pro_btn)
    iph_17_markup.add(iphone_17_pro_max_btn)
    bot.send_message(call.message.chat.id, "Выберите модель IPhone 17👇", reply_markup=iph_17_markup)


@bot.callback_query_handler(func=lambda call: call.data == "iphone_17_base")
def iphone_17_base_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 17\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 50%\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_17_air")
def iphone_17_air_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 17 Air\n<blockquote>Обзор: 147\nКоллиматор: 137\n2x: 132\n4x: 117\nСнайп прицел: 107\nСвободный обзор: 127\nКнопка огня: 52\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_17_pro")
def iphone_17_pro_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 17 Pro\n<blockquote>Обзор: 150\nКоллиматор: 140\n2x: 135\n4x: 120\nСнайп прицел: 110\nСвободный обзор: 130\nКнопка огня: 52\nDpi: Стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data == "iphone_17_pro_max")
def iphone_17_pro_max_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "⚙️Настройки IPhone 17 Pro Max\n<blockquote>Обзор: 152\nКоллиматор: 142\n2x: 137\n4x: 122\nСнайп прицел: 112\nСвободный обзор: 132\nКнопка огня: 54\nDpi: стандарт</blockquote>",
                     reply_markup=go_back_markup, parse_mode="html")


# ===== SAMSUNG =====
@bot.callback_query_handler(func=lambda call: call.data == "samsung")
def samsung_handler(call):
    bot.answer_callback_query(call.id)
    samsung_markup = types.InlineKeyboardMarkup()
    samsung_a_15_btn = types.InlineKeyboardButton("Samsung A15", callback_data="samsung_a_15")
    samsung_a_10_s_btn = types.InlineKeyboardButton("Samsung A10S", callback_data="samsung_a_10_s")
    samsung_markup.add(samsung_a_15_btn)
    samsung_markup.add(samsung_a_10_s_btn)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=samsung_markup)


@bot.callback_query_handler(func=lambda call: call.data == "samsung_a_15")
def samsung_a_15_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "<blockquote>обзор: 119\nколлиматор: 100\n2х: 172\n4х: 188\n8х: 120\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 582\nкнопка: 52</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


@bot.callback_query_handler(func=lambda call: call.data == "samsung_a_10_s")
def samsung_a_10_s_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "<blockquote>обзор: 199\nколлиматор: 190\n2х: 192\n4х: 193\n8х: 155\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 449\nкнопка: 39</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== REDMI =====
@bot.callback_query_handler(func=lambda call: call.data == "redmi")
def redmi_handler(call):
    bot.answer_callback_query(call.id)
    redmi_markup = types.InlineKeyboardMarkup()
    redmi_note_14 = types.InlineKeyboardButton("Redmi Note 14", callback_data="redmi_note_14")
    redmi_10_a = types.InlineKeyboardButton("Redmi 10A", callback_data="redmi_10_a")
    redmi_markup.add(redmi_note_14)
    redmi_markup.add(redmi_10_a)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=redmi_markup)


@bot.callback_query_handler(func=lambda call: call.data == "redmi_note_14")
def redmi_note_14_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "Настройки на Redmi Note 14\n<blockquote>обзор: 189\nколлиматор: 181\n2х: 175\n4х: 167\n8х: 111\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 40</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


@bot.callback_query_handler(func=lambda call: call.data == "redmi_10_a")
def redmi_10_a_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "Настройки на Redmi 10A\n<blockquote>обзор: 198\nколлиматор: 190\n2х: 177\n4х: 170\n8х: 110\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 510\nкнопка: 51</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== REALME =====
@bot.callback_query_handler(func=lambda call: call.data == "realme")
def realme_handler(call):
    bot.answer_callback_query(call.id)
    realme_markup = types.InlineKeyboardMarkup()
    realme_12_btn = types.InlineKeyboardButton("Realme 12", callback_data="realme_12")
    realme_8_btn = types.InlineKeyboardButton("Realme 8", callback_data="realme_8")
    realme_markup.add(realme_12_btn)
    realme_markup.add(realme_8_btn)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=realme_markup)


@bot.callback_query_handler(func=lambda call: call.data == "realme_12")
def realme_12_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "<blockquote>обзор: 188\nколлиматор: 180\n2х: 174\n4х: 168\n8х: 111\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 455\nкнопка: 50</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


@bot.callback_query_handler(func=lambda call: call.data == "realme_8")
def realme_8_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "<blockquote>обзор: 177\nколлиматор: 159\n2х: 174\n4х: 181\n8х: 172\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 500\nкнопка: 48</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== TECNO =====
@bot.callback_query_handler(func=lambda call: call.data == "tecno")
def tecno_handler(call):
    bot.answer_callback_query(call.id)
    tecno_markup = types.InlineKeyboardMarkup()
    tecno_spark_30 = types.InlineKeyboardButton("Tecno Spark 30", callback_data="tecno_spark_30")
    tecno_spark_7 = types.InlineKeyboardButton("Tecno Spark 7", callback_data="tecno_spark_7")
    tecno_markup.add(tecno_spark_30)
    tecno_markup.add(tecno_spark_7)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=tecno_markup)


@bot.callback_query_handler(func=lambda call: call.data == "tecno_spark_30")
def tecno_spark_30_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "<blockquote>обзор: 183\nколлиматор: 178\n2х: 165\n4х: 171\n8х: 150\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 480\nкнопка: 40</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


@bot.callback_query_handler(func=lambda call: call.data == "tecno_spark_7")
def tecno_spark_7_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "<blockquote>обзор: 192\nколлиматор: 188\n2х: 198\n4х: 155\n8х: 105\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 470\nкнопка: 37</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== POCO =====
@bot.callback_query_handler(func=lambda call: call.data == "poco")
def poco_handler(call):
    bot.answer_callback_query(call.id)
    poco_markup = types.InlineKeyboardMarkup()
    poco_x4_gt = types.InlineKeyboardButton("Poco X4 GT", callback_data="poco_x4_gt")
    poco_markup.add(poco_x4_gt)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=poco_markup)


@bot.callback_query_handler(func=lambda call: call.data == "poco_x4_gt")
def poco_x4_gt_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "Настройки на Poco X4 GT\n<blockquote>обзор: 197\nколлиматор: 188\n2х: 178\n4х: 170\n8х: 155\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 520\nкнопка: 45</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== HUAWEI =====
@bot.callback_query_handler(func=lambda call: call.data == "huawei")
def huawei_handler(call):
    bot.answer_callback_query(call.id)
    huawei_markup = types.InlineKeyboardMarkup()
    huawei_nova_8_i = types.InlineKeyboardButton("Huawei Nova 8I", callback_data="huawei_nova_8_i")
    huawei_markup.add(huawei_nova_8_i)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=huawei_markup)


@bot.callback_query_handler(func=lambda call: call.data == "huawei_nova_8_i")
def huawei_nova_8_i_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "Настройки на Huawei Nova 8I\n<blockquote>обзор: 200\nколлиматор: 167\n2х: 174\n4х: 106\n8х: 91\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 458\nкнопка: 44</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== HONOR =====
@bot.callback_query_handler(func=lambda call: call.data == "honor")
def honor_handler(call):
    bot.answer_callback_query(call.id)
    honor_markup = types.InlineKeyboardMarkup()
    honor_10_x_lite = types.InlineKeyboardButton("Honor 10X Lite", callback_data="honor_10_x_lite")
    honor_markup.add(honor_10_x_lite)
    bot.send_message(call.message.chat.id, "Выберите свою модель ниже👇", reply_markup=honor_markup)


@bot.callback_query_handler(func=lambda call: call.data == "honor_10_x_lite")
def honor_10_x_lite_handler(call):
    bot.answer_callback_query(call.id)
    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    bot.send_message(call.message.chat.id,
                     "Настройки на Honor 10X Lite\n<blockquote>обзор: 192\nколлиматор: 177\n2х: 178\n4х: 154\n8х: 150\nсвободный обзор: на свое усмотрение ( рекомендую 150 )\nDpi: 485\nкнопка: 39</blockquote>",
                     parse_mode="html", reply_markup=go_back_markup)


# ===== КНОПКА НАЗАД =====
@bot.callback_query_handler(func=lambda call: call.data == "back")
def back_handler(call):
    bot.answer_callback_query(call.id)
    markup_menu_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
    iphone_btn = types.KeyboardButton("🍎IPhone🍎")
    android_btn = types.KeyboardButton("🤖Android🤖")
    coders_btn = types.KeyboardButton("ℹ️Разработчикиℹ️")
    cooperation_btn = types.KeyboardButton("🤳Сотрудничество🤳")
    markup_menu_buttons.add(iphone_btn, android_btn)
    markup_menu_buttons.add(coders_btn, cooperation_btn)

    try:
        if os.path.exists("menu_logo.jpg"):
            with open("menu_logo.jpg", "rb") as menu_logo:
                bot.send_photo(call.message.chat.id, menu_logo,
                               caption="<blockquote>📋Вы вернулись в меню!📋</blockquote>",
                               reply_markup=markup_menu_buttons, parse_mode="html")
        else:
            bot.send_message(call.message.chat.id, "📋Вы вернулись в меню!📋",
                             reply_markup=markup_menu_buttons)
    except:
        bot.send_message(call.message.chat.id, "📋Вы вернулись в меню!📋",
                         reply_markup=markup_menu_buttons)


# ===== ОБРАБОТКА СООБЩЕНИЙ =====
@bot.message_handler(func=lambda message: True)
def phone_value(message):
    # Пропускаем команды (начинаются с /)
    if message.text and message.text.startswith('/'):
        return

    if message.text == "🍎IPhone🍎":
        iphone_markup = types.InlineKeyboardMarkup()
        iphone_7_btn = types.InlineKeyboardButton("⚙️IPhone 7", callback_data="iphone_7")
        iphone_8_btn = types.InlineKeyboardButton("⚙️IPhone 8", callback_data="iphone_8")
        iphone_10_btn = types.InlineKeyboardButton("⚙️IPhone X (10)", callback_data="iphone_10")
        iphone_11_btn = types.InlineKeyboardButton("⚙️IPhone 11", callback_data="iphone_11")
        iphone_12_btn = types.InlineKeyboardButton("⚙️IPhone 12", callback_data="iphone_12")
        iphone_13_btn = types.InlineKeyboardButton("⚙️IPhone 13", callback_data="iphone_13")
        iphone_14_btn = types.InlineKeyboardButton("⚙️IPhone 14", callback_data="iphone_14")
        iphone_15_btn = types.InlineKeyboardButton("⚙️IPhone 15", callback_data="iphone_15")
        iphone_16_btn = types.InlineKeyboardButton("⚙️IPhone 16", callback_data="iphone_16")
        iphone_17_btn = types.InlineKeyboardButton("⚙️IPhone 17", callback_data="iphone_17")
        go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")

        iphone_markup.add(iphone_7_btn)
        iphone_markup.add(iphone_8_btn)
        iphone_markup.add(iphone_10_btn)
        iphone_markup.add(iphone_11_btn)
        iphone_markup.add(iphone_12_btn)
        iphone_markup.add(iphone_13_btn)
        iphone_markup.add(iphone_14_btn)
        iphone_markup.add(iphone_15_btn)
        iphone_markup.add(iphone_16_btn)
        iphone_markup.add(iphone_17_btn)
        iphone_markup.add(go_back_btn)

        try:
            if os.path.exists("iphone_sittings.jpg"):
                with open("iphone_sittings.jpg", "rb") as menu_logo:
                    bot.send_photo(message.chat.id, menu_logo,
                                   caption="<blockquote>Выберите свой IPhone из списка!</blockquote>",
                                   reply_markup=iphone_markup, parse_mode="html")
            else:
                bot.send_message(message.chat.id, "Выберите свой IPhone из списка!",
                                 reply_markup=iphone_markup)
        except:
            bot.send_message(message.chat.id, "Выберите свой IPhone из списка!",
                             reply_markup=iphone_markup)

    elif message.text == "🤖Android🤖":
        android_markup = types.InlineKeyboardMarkup()
        samsung_btn = types.InlineKeyboardButton("Samsung", callback_data="samsung")
        realme_btn = types.InlineKeyboardButton("Realme", callback_data="realme")
        poco_btn = types.InlineKeyboardButton("Poco", callback_data="poco")
        redmi_btn = types.InlineKeyboardButton("Redmi", callback_data="redmi")
        tecno_btn = types.InlineKeyboardButton("Tecno", callback_data="tecno")
        huawei_btn = types.InlineKeyboardButton("Huawei", callback_data="huawei")
        honor_btn = types.InlineKeyboardButton("Honor", callback_data="honor")
        go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")

        android_markup.add(samsung_btn)
        android_markup.add(realme_btn)
        android_markup.add(poco_btn)
        android_markup.add(redmi_btn)
        android_markup.add(tecno_btn)
        android_markup.add(huawei_btn)
        android_markup.add(honor_btn)
        android_markup.add(go_back_btn)

        try:
            if os.path.exists("android_sittings.jpg"):
                with open("android_sittings.jpg", "rb") as android_sittings:
                    bot.send_photo(message.chat.id, android_sittings,
                                   caption="<blockquote>Выберите свой Android в списке👇</blockquote>",
                                   reply_markup=android_markup, parse_mode="html")
            else:
                bot.send_message(message.chat.id, "Выберите свой Android в списке👇",
                                 reply_markup=android_markup)
        except:
            bot.send_message(message.chat.id, "Выберите свой Android в списке👇",
                             reply_markup=android_markup)

    elif message.text == "ℹ️Разработчикиℹ️":
        markup_back = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_btn = types.KeyboardButton("🔙 Назад")
        markup_back.add(back_btn)
        bot.send_message(message.chat.id, "✅Главные разработчики✅:\n\n @Acash_ff\n @JustF12", reply_markup=markup_back)

    elif message.text == "🤳Сотрудничество🤳":
        markup_back = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_btn = types.KeyboardButton("🔙 Назад")
        markup_back.add(back_btn)
        bot.send_message(message.chat.id, "Пишите сюда 👇\n\n@Acash_ff", reply_markup=markup_back)

    elif message.text == "🔙 Назад":
        go_back_func(message)

    elif message.text and not message.text.startswith('/'):
        send_main_menu(message)


# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("=" * 50)
    print("БОТ ЗАПУЩЕН")
    print("=" * 50)
    print("Админы:", ADMINS)
    print("Токен:", TOKEN)
    print("=" * 50)
    print("РЕКЛАМА ПРИ /START:")
    print(f"Статус: {'ВКЛЮЧЕНА' if ad_enabled else 'ВЫКЛЮЧЕНА'}")
    print(f"Позиция: {'ДО меню' if ad_position == 'before' else 'ПОСЛЕ меню'}")
    print(f"Задержка: {ad_delay} сек.")
    print(f"Фото: {'✅' if ad_photo_id else '❌'}")
    print("=" * 50)
    print("Для остановки нажмите Ctrl+C")
    print("=" * 50)

    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Ошибка: {e}")
            print("Перезапуск через 5 секунд...")
            time.sleep(5)
