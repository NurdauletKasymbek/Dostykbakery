import telebot
from telebot import types

# Конфигурация
BOT_TOKEN = "7817614647:AAHvxIBmJTzukPvzgkzkIVM8Ww_AE-pqVFk"
ADMIN_ID = 6529188202  # Админнің Telegram ID-н осында жазыңыз

KASPI_NUMBER_1 = "+77752549373"
KASPI_NUMBER_2 = "+77078754556"
KASPI_LINK = "https://kaspi.kz/transfers"

BREAD_PRICE = 150  # Нан бағасы

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}
COMMAND_BUTTONS = ["🍞 Нанға тапсырыс беру", "📞 Байланыс нөмірі"]

def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🍞 Нанға тапсырыс беру", "📞 Байланыс нөмірі")
    return markup

def reset_user_state(chat_id):
    user_data[chat_id] = {}

@bot.message_handler(commands=['start'])
def start_handler(message):
    reset_user_state(message.chat.id)
    bot.send_message(message.chat.id, "Төмендегі мәзірден таңдаңыз:", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "📞 Байланыс нөмірі")
def contact_info(message):
    reset_user_state(message.chat.id)
    bot.send_message(
        message.chat.id,
        f"📞 {KASPI_NUMBER_1}\n📞 {KASPI_NUMBER_2}",
        reply_markup=main_menu_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "🍞 Нанға тапсырыс беру")
def order_bread(message):
    chat_id = message.chat.id
    reset_user_state(chat_id)
    bot.send_message(chat_id, "👤 Аты-жөніңізді жазыңыз:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    if message.text in COMMAND_BUTTONS:
        return start_handler(message)
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text
    bot.send_message(chat_id, "📞 Телефон нөміріңізді жазыңыз:")
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    if message.text in COMMAND_BUTTONS:
        return start_handler(message)
    chat_id = message.chat.id
    user_data[chat_id]['phone'] = message.text
    bot.send_message(chat_id, "🍞 Қанша нан қажет екенін жазыңыз (мысалы, 2):")
    bot.register_next_step_handler(message, get_quantity)

def get_quantity(message):
    if message.text in COMMAND_BUTTONS:
        return start_handler(message)
    chat_id = message.chat.id
    qty = message.text.strip()
    if not qty.isdigit():
        bot.send_message(chat_id, "Санмен жазыңыз. Қайтадан:")
        return bot.register_next_step_handler(message, get_quantity)

    user_data[chat_id]['quantity'] = int(qty)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("🚚 Жеткізу керек", "❌ Жеткізу қажет емес")
    bot.send_message(chat_id, "Жеткізу керек пе?", reply_markup=markup)
    bot.register_next_step_handler(message, get_delivery)

def get_delivery(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if text == "🚚 Жеткізу керек":
        bot.send_message(chat_id, "📍 Мекенжайыңызды жазыңыз:")
        bot.register_next_step_handler(message, get_address)
    elif text == "❌ Жеткізу қажет емес":
        user_data[chat_id]['address'] = "Жеткізу қажет емес"
        show_summary(chat_id)
    else:
        bot.send_message(chat_id, "Тек төмендегі батырмалардың бірін таңдаңыз:")
        return bot.register_next_step_handler(message, get_delivery)

def get_address(message):
    chat_id = message.chat.id
    user_data[chat_id]['address'] = message.text
    show_summary(chat_id)

def show_summary(chat_id):
    data = user_data[chat_id]
    quantity = data['quantity']
    total = quantity * BREAD_PRICE

    data['total'] = total

    delivery_note = f"📦 Жеткізу: {data['address']}"
    total_note = f"💰 Жалпы сома: {total} т"
    kaspi_notice = "📄 Kaspi арқылы төлем жасасаңыз, төлем чегін осы чатқа PDF түрінде жіберіңіз.\n📑 *Тек PDF форматтағы чек жіберіңіз.*"

    summary = (
        f"*Тапсырыс мәліметтері:*\n"
        f"👤 Аты-жөні: {data['name']}\n"
        f"📞 Тел: {data['phone']}\n"
        f"🍞 Нан саны: {quantity}\n"
        f"{delivery_note}\n"
        f"{total_note}\n\n"
        f"{kaspi_notice}\n\n"
        f"Төлем жасау үшін төмендегі сілтемені басыңыз:"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏦 Kaspi арқылы төлеу", url=KASPI_LINK))
    markup.add(types.InlineKeyboardButton("💰 Қолма-қол төлем", callback_data="cash_payment"))

    bot.send_message(chat_id, summary, parse_mode="Markdown", reply_markup=markup)

    # Админге жіберу
    bot.send_message(ADMIN_ID, f"📥 Жаңа тапсырыс:\n👤 {data['name']}\n📞 {data['phone']}\n🍞 {quantity} нан\n{delivery_note}\n💰 Сома: {total} т")

@bot.callback_query_handler(func=lambda call: call.data == "cash_payment")
def handle_cash_payment(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "✅ Қолма-қол төлем таңдалды. Тапсырысыңыз өңделуде. Рақмет!", reply_markup=main_menu_keyboard())

@bot.message_handler(content_types=['document'])
def handle_pdf_check(message):
    chat_id = message.chat.id
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.send_message(chat_id, "⚠️ Тек PDF форматтағы чек қабылданады.")
        return

    data = user_data.get(chat_id, {})
    if not data:
        bot.send_message(chat_id, "Қате: тапсырыс деректері табылмады.")
        return

    caption = (
        f"📄 Клиенттен чек келді:\n"
        f"👤 {data.get('name', '-')}\n"
        f"📞 {data.get('phone', '-')}\n"
        f"🍞 {data.get('quantity', '-')}\n"
        f"📦 {data.get('address', '-')}\n"
        f"💰 {data.get('total', '-')} т"
    )

    bot.send_message(chat_id, "✅ Төлем чегі қабылданды. Тапсырысыңыз өңделуде. Рақмет!", reply_markup=main_menu_keyboard())
    bot.send_document(ADMIN_ID, message.document.file_id, caption=caption)

# Ботты іске қосу
bot.polling(none_stop=True)

