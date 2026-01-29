import telebot
from telebot import types


TOKEN = "8564117995:AAEWiVbO7dx1PuMSGnhRt2rj7snn6tRas0g"
bot = telebot.TeleBot(TOKEN)

# ===== Проверка подписки =====
def check_sub(user_id):
    try:
        member = bot.get_chat_member("@Acash_05", user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# ===== Старт бота =====
@bot.message_handler(commands=["start"])
def private_hendler(message):
    if not check_sub(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        subscribe_btn = types.InlineKeyboardButton("📢 Подписаться", url="https://t.me/Acash_05")
        check_sub_btn = types.InlineKeyboardButton("🟢 Проверить", callback_data="check_sub")
        markup.add(subscribe_btn)
        markup.add(check_sub_btn)
        bot.send_message(
            message.chat.id,
            "Вы не подписаны на наш телеграмм канал!\nБот заработает после подписки!",
            reply_markup=markup
        )
        return
    else:
        send_main_menu(message)

# ===== Главная меню функция =====
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

# ===== Обработка кнопки Проверить подписку =====
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_button(call):
    if check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Вы подписаны! Можно пользоваться ботом.", show_alert=True)
        send_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны на канал!", show_alert=True)


# ===== Обработка сообщений пользователя =====
@bot.message_handler(func=lambda message: True)
def phone_value(message):
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
        with open("iphone_sittings.jpg", "rb") as menu_logo:
            bot.send_photo(message.chat.id,menu_logo,caption="<blockquote>Выберите свой IPhone из списка!</blockquote>", reply_markup=iphone_markup, parse_mode="html")

    elif message.text == "🤖Android🤖":
        android_markup = types.InlineKeyboardMarkup()
        samsung_btn = types.InlineKeyboardButton("Samsung", callback_data="samsung")
        realme_btn = types.InlineKeyboardButton("Realme", callback_data="realme")
        poco_btn = types.InlineKeyboardButton("Poco", callback_data="poco")
        redmi_btn = types.InlineKeyboardButton("Redmi", callback_data="redmi")
        tecno_btn = types.InlineKeyboardButton("Tecno", callback_data="tecno")
        go_back_samsung_btn = types.InlineKeyboardButton("Назад", callback_data="back")
        android_markup.add(samsung_btn)
        android_markup.add(realme_btn)
        android_markup.add(poco_btn)
        android_markup.add(redmi_btn)
        android_markup.add(tecno_btn)
        android_markup.add(go_back_samsung_btn)
        with open("android_sittings.jpg", "rb") as android_sittings:
            bot.send_photo(message.chat.id,android_sittings,caption="<blockquote>Выберите свой Android в списке👇</blockquote>", reply_markup=android_markup, parse_mode="html")

    elif message.text == "ℹ️Разработчикиℹ️":
        markup_back = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_btn = types.KeyboardButton("Назад")
        markup_back.add(back_btn)
        bot.send_message(message.chat.id, "✅Главные разработчики✅:\n\n @Acash_ff\n @JustF12", reply_markup=markup_back)
    elif message.text == "🤳Сотрудничество🤳":
        bot.send_message(message.chat.id, "Пишите сюда 👇\n\n@Acash_ff")

    elif message.text == "Назад":
        go_back_func(message)

# ===== Callback handler =====
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    go_back_markup = types.InlineKeyboardMarkup()
    go_back_btn = types.InlineKeyboardButton("🔙Назад🔙", callback_data="back")
    go_back_markup.add(go_back_btn)
    #========== Samsung =========
    if call.data == "samsung":
        bot.answer_callback_query(call.id)
        with open("samsung_sittings.jpg", "rb") as samsung_sittings:
            bot.send_photo(call.message.chat.id,samsung_sittings ,caption="Настроойки Samsung\n<blockquote>Обзор: 184\nКоллиматор: 190\n2х Прицел: 185\n4х Прицел: 178\nСнайперский Прицел: 80\nСвободный Обзор: 0\nКнопка огня: 45\nDpi: 590</blockquote>", reply_markup=go_back_markup, parse_mode="html")
        #==== Realme ===
    if call.data == "redmi":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,"Настройки на Redmi\n<blockquote>Обзор: 197\nКоллиматор: 187\n2х Прицел: 187\n4х Прицел: 187\nСнайперский Прицел: 187\nКнопка Свободный Камеры: 187\nКнопка Огня: 51\nDpi: 587</blockquote>",reply_markup=go_back_markup, parse_mode="html")
    
    #======== Tecno ========
    if call.data == "tecno":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Настройки на Tecno\n<blockquote>обзор: 183\nколлиматор: 178\n2х: 165\n4х: 171\n8х: 150\nскорость указателя: 50%\nDpi: 480</blockquote>",reply_markup=go_back_btn, parse_mode="html")
    
    if call.data == "realme":
        bot.answer_callback_query(call.id)
        with open("realme_sittings.jpg", "rb") as realme_sittings:
            bot.send_photo(call.message.chat.id, realme_sittings ,caption="Настройки на Realme\n<blockquote>Обзор 200\nКолиматор 50\n2х 60\n4х 60\nСнайп прицел 200\nСвободный обзор 200\nКнопка огня 51\nДпиай 470</blockquote>", reply_markup=go_back_markup, parse_mode="html")
        #===== Poco =======
    if call.data == "poco":
        bot.answer_callback_query(call.id)
        with open("poco_sittings.jpg", "rb") as poco_sittings:
            bot.send_photo(call.message.chat.id, poco_sittings ,caption="Настройки на Poco\n<blockquote>Обзор 194\nКолиматор 174\n2х 134\n4х 179\nСнайп прицел 154\nСвободный обзор 52\nКнопка огня 52\nДпиай 433</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    # ===== iPhone 7 =====
    if call.data == "iphone_7":
        iph_7_markup = types.InlineKeyboardMarkup()
        iphone_7_base_btn = types.InlineKeyboardButton("IPhone 7", callback_data="iphone_7_base")
        iphone_7_plus_btn = types.InlineKeyboardButton("IPhone 7 Plus", callback_data="iphone_7_plus")
        iph_7_markup.add(iphone_7_base_btn)
        iph_7_markup.add(iphone_7_plus_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 7👇", reply_markup=iph_7_markup, parse_mode="html")
    elif call.data == "iphone_7_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 7 Base\n<blockquote>DPI 31\nОбзор 170\nКоллиматор 198\n2x 200 741\n4x 200\nСнайп прицел 200\nСвободный обзор 200\nКнопка 44 </blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_7_plus":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 7 Plus\n<blockquote>DPI 54\nОбзор 178\nКоллиматор 152\n2x 129\n4х 121\nСнайп прицел 137\nСвободный обзор 76\nКнопка огня: 46 </blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 8 =====
    if call.data == "iphone_8":
        iph_8_markup = types.InlineKeyboardMarkup()
        iphone_8_base_btn = types.InlineKeyboardButton("IPhone 8", callback_data="iphone_8_base")
        iphone_8_plus_btn = types.InlineKeyboardButton("IPhone 8 Plus", callback_data="iphone_8_plus")
        iph_8_markup.add(iphone_8_base_btn)
        iph_8_markup.add(iphone_8_plus_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 8👇", reply_markup=iph_8_markup, parse_mode="html")
    elif call.data == "iphone_8_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 8 Base\n<blockquote>Обзор: 167\nКоллиматор: 185\n2x Прицел: 181\n4x Прицел: 173\nКнопка: 50%\nDPI: Стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_8_plus":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 8 Plus<blockquote>\nDPI 31\nОбзор 100\nКоллиматор 187\n2x 200\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone X (10) =====
    if call.data == "iphone_10":
        iph_10_markup = types.InlineKeyboardMarkup()
        iphone_10_base_btn = types.InlineKeyboardButton("IPhone X", callback_data="iphone_10_base")
        iphone_10_s_btn = types.InlineKeyboardButton("IPhone XS", callback_data="iphone_10_s")
        iphone_10_x_r_btn = types.InlineKeyboardButton("IPhone XR", callback_data="iphone_x_r")
        iphone_10_s_max_btn = types.InlineKeyboardButton("IPhone XS Max", callback_data="iphone_10_s_max")
        iph_10_markup.add(iphone_10_base_btn)
        iph_10_markup.add(iphone_10_x_r_btn)
        iph_10_markup.add(iphone_10_s_btn)
        iph_10_markup.add(iphone_10_s_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone X👇", reply_markup=iph_10_markup)
    elif call.data == "iphone_x_r":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone XR\n<blockquote>Dpi 120\nобзор 129\nКоллиматор 99\n2x 156\n4x 164\nСнайп прицел 100\nСвободный обзор 100\nКнопка огня 36</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_10_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone X Base\n<blockquote>Dpi 31\nОбзор 177\nКоллиматор 195\n2x 198\n4x 20\nСнайп прицел 200\nСвободный обзор 200\nКнопка 49</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_10_s":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone XS\n<blockquote>Dpi 49\nОбзор 100\nКоллиматор 120\n2x 100\n4x 200\nСнайп прицел 200\nСвободный обзор 100\nКнопка 44</blockquote>", reply_markup=go_back_markup)
    elif call.data == "iphone_10_s_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настоойки на IPhone XS Max\n<blockquote>Обзор: 175\nКоллиматор: 185\n2x Прицел: 195\n4x Прицел: 173\nКнопка: 53%\nDPI: 31</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 11 =====
    if call.data == "iphone_11":
        iph_11_markup = types.InlineKeyboardMarkup()
        iphone_11_base_btn = types.InlineKeyboardButton("IPhone 11", callback_data="iphone_11_base")
        iphone_11_pro_btn = types.InlineKeyboardButton("IPhone 11 Pro", callback_data="iphone_11_pro")
        iphone_11_pro_max_btn = types.InlineKeyboardButton("IPhone 11 Pro Max", callback_data="iphone_11_pro_max")
        iph_11_markup.add(iphone_11_base_btn)
        iph_11_markup.add(iphone_11_pro_btn)
        iph_11_markup.add(iphone_11_pro_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 11👇", reply_markup=iph_11_markup)
    elif call.data == "iphone_11_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 11\n<blockquote>Обзор 149\nКоллиматор 150\n2х 200\n4х 180\nСнайп прицел 200\nСвободный обзор 200\nКнопка огня 39\nDPI: 31</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_11_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 11 Pro\n<blockquote>обзор:170\nколлиматор:165\n2х прицел:155\n4х прицел:135\nснайперский прицел:110\nСвободная камера:130\n58-62 кнопка огня</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_11_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки на IPhone 11 Pro Max\n<blockquote>Обзор 108\nКоллиматор  94\n2x 125\n4x 124\nСнайп прицел 66\nСвободный обзор 41\nDpi: 100\nКнопка огня: 45</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 12 =====
    if call.data == "iphone_12":
        iph_12_markup = types.InlineKeyboardMarkup()
        iphone_12_base_btn = types.InlineKeyboardButton("IPhone 12", callback_data="iphone_12_base")
        iphone_12_mini_btn = types.InlineKeyboardButton("IPhone 12 Mini", callback_data="iphone_12_mini")
        iphone_12_pro_btn = types.InlineKeyboardButton("IPhone 12 Pro", callback_data="iphone_12_pro")
        iphone_12_pro_max_btn = types.InlineKeyboardButton("IPhone 12 Pro Max", callback_data="iphone_12_pro_max")
        iph_12_markup.add(iphone_12_base_btn)
        iph_12_markup.add(iphone_12_mini_btn)
        iph_12_markup.add(iphone_12_pro_btn)
        iph_12_markup.add(iphone_12_pro_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 12👇", reply_markup=iph_12_markup)
    elif call.data == "iphone_12_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 12\n<blockquote>Обзор: 165\nКоллиматор: 158\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 50\nDpi: 33</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_12_mini":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 12 Mini\n<blockquote>Обзор: 158\nКоллиматор: 150\n2x: 135\n4x: 115\nСнайп прицел: 95\nСвободный обзор: 105\nКнопка огня: 48\nDpi</blockquote>: 42", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_12_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 12 Pro\n<blockquote>Обзор: 168\nКоллиматор: 160\n2x: 145\n4x: 125\nСнайп прицел: 100\nСвободный обзор: 112\nКнопка огня: 50\nDpi: 35</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_12_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 12 Pro Max\n<blockquote>Обзор: 172\nКоллиматор: 165\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 52\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 13 =====
    if call.data == "iphone_13":
        iph_13_markup = types.InlineKeyboardMarkup()
        iphone_13_base_btn = types.InlineKeyboardButton("IPhone 13", callback_data="iphone_13_base")
        iphone_13_mini_btn = types.InlineKeyboardButton("IPhone 13 Mini", callback_data="iphone_13_mini")
        iphone_13_pro_btn = types.InlineKeyboardButton("IPhone 13 Pro", callback_data="iphone_13_pro")
        iphone_13_pro_max_btn = types.InlineKeyboardButton("IPhone 13 Pro Max", callback_data="iphone_13_pro_max")
        iph_13_markup.add(iphone_13_base_btn)
        iph_13_markup.add(iphone_13_mini_btn)
        iph_13_markup.add(iphone_13_pro_btn)
        iph_13_markup.add(iphone_13_pro_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 13👇", reply_markup=iph_13_markup)
    elif call.data == "iphone_13_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 13\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 120\nКнопка огня: 50\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_13_mini":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 13 Mini\n<blockquote>Обзор: 170\nКоллиматор: 162\n2x: 142\n4x: 122\nСнайп прицел: 98\nСвободный обзор: 110\nКнопка огня: 48\nDpi: Стандарт</blockquote>",reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_13_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 13 Pro\n<blockquote>Обзор: 161\nКоллиматор: 168\n2x: 148\n4x: 128\nСнайп прицел: 102\nСвободный обзор: 115\nКнопка огня: 50%\nDpi: 53</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_13_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 13 Pro Max\n<blockquote>Обзор: 178\nКоллиматор: 170\n2x: 150\n4x: 130\nСнайп прицел: 105\nСвободный обзор: 118\nКнопка огня: 52\nДпиай: 37</blockquote>", reply_markup=go_back_markup, parse_mode="html")


    # ===== iPhone 14 =====
    if call.data == "iphone_14":
        iph_14_markup = types.InlineKeyboardMarkup()
        iphone_14_base_btn = types.InlineKeyboardButton("IPhone 14", callback_data="iphone_14_base")
        iphone_14_plus_btn = types.InlineKeyboardButton("IPhone 14 Plus", callback_data="iphone_14_plus")
        iphone_14_pro_btn = types.InlineKeyboardButton("IPhone 14 Pro", callback_data="iphone_14_pro")
        iphone_14_pro_max_btn = types.InlineKeyboardButton("IPhone 14 Pro Max", callback_data="iphone_14_pro_max")
        iph_14_markup.add(iphone_14_base_btn)
        iph_14_markup.add(iphone_14_plus_btn)
        iph_14_markup.add(iphone_14_pro_btn)
        iph_14_markup.add(iphone_14_pro_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 14👇", reply_markup=iph_14_markup)
    elif call.data == "iphone_14_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 14\n<blockquote>Обзор: 180\nКоллиматор: 172\n2x: 152\n4x: 132\nСнайп прицел: 107\nСвободный обзор: 120\nКнопка огня: 50\nДпиай: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_14_plus":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 14 Plus\n<blockquote>Обзор: 185\nКоллиматор: 176\n2x: 158\n4x: 138\nСнайп прицел: 110\nСвободный обзор: 125\nКнопка огня: 54\nДпиай: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_14_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 14 Pro\n<blockquote>Обзор: 187\nКоллиматор: 178\n2x: 160\n4x: 140\nСнайп прицел: 112\nСвободный обзор: 127\nКнопка огня: 52\nDpi: Стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_14_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 14 Pro Max\n<blockquote>Обзор: 190\nКоллиматор: 182\n2x: 162\n4x: 142\nСнайп прицел: 115\nСвободный обзор: 130\nКнопка огня: 54\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 15 =====
    if call.data == "iphone_15":
        iph_15_markup = types.InlineKeyboardMarkup()
        iphone_15_base_btn = types.InlineKeyboardButton("IPhone 15", callback_data="iphone_15_base")
        iphone_15_plus_btn = types.InlineKeyboardButton("IPhone 15 Plus", callback_data="iphone_15_plus")
        iphone_15_pro_btn = types.InlineKeyboardButton("IPhone 15 Pro", callback_data="iphone_15_pro")
        iphone_15_pro_max_btn = types.InlineKeyboardButton("IPhone 15 Pro Max", callback_data="iphone_15_pro_max")
        iph_15_markup.add(iphone_15_base_btn)
        iph_15_markup.add(iphone_15_plus_btn)
        iph_15_markup.add(iphone_15_pro_btn)
        iph_15_markup.add(iphone_15_pro_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 15👇", reply_markup=iph_15_markup)
    elif call.data == "iphone_15_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 15\n<blockquote>Обзор: 192\nКоллиматор: 184\n2x: 164\n4x: 144\nСнайп прицел: 117\nСвободный обзор: 132\nКнопка огня: 50\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_15_plus":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 15 Plus\n<blockquote>Обзор: 195\nКоллиматор: 186\n2x: 166\n4x: 146\nСнайп прицел: 118\nСвободный обзор: 134\nКнопка огня: 52\nDpi: Стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_15_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 15 Pro\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 120\nСвободный обзор: 136\nКнопка огня: 52\nDpi: Стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_15_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 15 Pro Max\n<blockquote>Обзор: 200\nКоллиматор: 190\n2x: 170\n4x: 150\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 54\nDpi: Стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 16 =====
    if call.data == "iphone_16":
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
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 16👇", reply_markup=iph_16_markup)
    elif call.data == "iphone_16_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 16\n<blockquote>Обзор: 195\nКоллиматор: 185\n2x: 165\n4x: 145\nСнайп прицел: 120\nСвободный обзор: 135\nКнопка огня: 50\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_16_e":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 16e\n<blockquote>Обзор: 138\nКоллиматор: 128\n2x: 123\n4x: 108\nСнайп прицел: 98\nСвободный обзор: 118\nКнопка огня: 50\nDpi: стандарт</blockquote>")
    elif call.data == "iphone_16_plus":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 16 Plus\n<blockquote>Обзор: 198\nКоллиматор: 188\n2x: 168\n4x: 148\nСнайп прицел: 122\nСвободный обзор: 138\nКнопка огня: 52\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_16_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 16 Pro\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 52\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_16_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Здесь будут настройки IPhone 16 Pro Max\n<blockquote>Обзор: 148\nКоллиматор: 138\n2x: 133\n4x: 118\nСнайп прицел: 108\nСвободный обзор: 128\nКнопка огня: 54\nДпиай: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== iPhone 17 =====
    if call.data == "iphone_17":
        iph_17_markup = types.InlineKeyboardMarkup()
        iphone_17_base_btn = types.InlineKeyboardButton("IPhone 17", callback_data="iphone_17_base")
        iphone_17_air_btn = types.InlineKeyboardButton("IPhone 17 Air", callback_data="iphone_17_air")
        iphone_17_pro_btn = types.InlineKeyboardButton("IPhone 17 Pro", callback_data="iphone_17_pro")
        iphone_17_pro_max_btn = types.InlineKeyboardButton("IPhone 17 Pro Max", callback_data="iphone_17_pro_max")
        iph_17_markup.add(iphone_17_base_btn)
        iph_17_markup.add(iphone_17_air_btn)
        iph_17_markup.add(iphone_17_pro_btn)
        iph_17_markup.add(iphone_17_pro_max_btn)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Выберите модель IPhone 17👇", reply_markup=iph_17_markup)
    elif call.data == "iphone_17_base":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 17\n<blockquote>Обзор: 145\nКоллиматор: 135\n2x: 130\n4x: 115\nСнайп прицел: 105\nСвободный обзор: 125\nКнопка огня: 50%\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_17_air":
        bot.answer_callback_query(call.id)      
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 17 Air\n<blockquote>Обзор: 147\nКоллиматор: 137\n2x: 132\n4x: 117\nСнайп прицел: 107\nСвободный обзор: 127\nКнопка огня: 52\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_17_pro":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 17 Pro\n<blockquote>Обзор: 150\nКоллиматор: 140\n2x: 135\n4x: 120\nСнайп прицел: 110\nСвободный обзор: 130\nКнопка огня: 52\nDpi: Стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")
    elif call.data == "iphone_17_pro_max":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️Настройки IPhone 17 Pro Max\n<blockquote>Обзор: 152\nКоллиматор: 142\n2x: 137\n4x: 122\nСнайп прицел: 112\nСвободный обзор: 132\nКнопка огня: 54\nDpi: стандарт</blockquote>", reply_markup=go_back_markup, parse_mode="html")

    # ===== Кнопка Назад =====
    if call.data == "back":
        markup_menu_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup_menu_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
        iphone_btn = types.KeyboardButton("🍎IPhone🍎")
        android_btn = types.KeyboardButton("🤖Android🤖")
        coders_btn = types.KeyboardButton("ℹ️Разработчикиℹ️")
        cooperation_btn = types.KeyboardButton("🤳Сотрудничество🤳")
        markup_menu_buttons.add(iphone_btn, android_btn)
        markup_menu_buttons.add(coders_btn, cooperation_btn)
        with open("menu_logo.jpg", "rb") as menu_logo:
            bot.send_photo(call.message.chat.id,menu_logo, caption= "<blockquote>Вы вернулись в меню!</blockquote>", reply_markup=markup_menu_buttons, parse_mode="html")


# ===== Функция возврата =====
def go_back_func(message):
    markup_menu_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
    iphone_btn = types.KeyboardButton("🍎IPhone🍎")
    android_btn = types.KeyboardButton("🤖Android🤖")
    coders_btn = types.KeyboardButton("ℹ️Разработчикиℹ️")
    cooperation_btn = types.KeyboardButton("🤳Сотрудничество🤳")
    markup_menu_buttons.add(iphone_btn, android_btn)
    markup_menu_buttons.add(coders_btn, cooperation_btn)
    with open("menu_logo.jpg", "rb") as menu_logo:
        bot.send_photo(message.chat.id,menu_logo,caption= "<blockquote>📋Вы вернулись в меню!📋</blockquote>", reply_markup=markup_menu_buttons,parse_mode="html")


bot.polling(non_stop=True)
