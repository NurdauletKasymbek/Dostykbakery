from flask import Flask, request
import telebot
import os

# Қауіпсіздік үшін токенді ортадан аламыз
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '6529188202'))

KASPI_NUMBER_1 = "+77752549373"
KASPI_NUMBER_2 = "+77078754556"
KASPI_LINK = "https://kaspi.kz/transfers"
BREAD_PRICE = 150

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
user_data = {}

COMMAND_BUTTONS = ["🍞 Нанға тапсырыс беру", "📞 Байланыс нөмірі"]

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    bot.process_new_updates([update])
    return '', 200

def main_menu_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(*COMMAND_BUTTONS)
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
    bot.send_message(message.chat.id, f"📞 {KASPI_NUMBER_1}\n📞 {KASPI_NUMBER_2}", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "🍞 Нанға тапсырыс беру")
def order_bread(message):
    chat_id = message.chat.id
    reset_user_state(chat_id)
    bot.send_message(chat_id, "👤 Аты-жөніңізді жазыңыз:", reply_markup=telebot.types.ReplyKeyboardRemove())
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
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
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
        bot.send_message(chat_id, "Төмендегі батырмалардың бірін таңдаңыз:")
        return bot.register_next_step_handler(message, get_delivery)

def get_address(message):
    chat_id = message.chat.id
    user_data[chat_id]['address'] = message.text
    show_summary(chat_id)

def show_summary(chat_id):
    data = user_data[chat_id]
    total = data['quantity'] * BREAD_PRICE
    data['total'] = total

    summary = (
        f"*Тапсырыс мәліметтері:*\n"
        f"👤 Аты-жөні: {data['name']}\n"
        f"📞 Тел: {data['phone']}\n"
        f"🍞 Нан саны: {data['quantity']}\n"
        f"📦 Жеткізу: {data['address']}\n"
        f"💰 Жалпы сома: {total} т\n\n"
        f"📄 Kaspi арқылы төлем чегін PDF форматында осы чатқа жіберіңіз.\n\n"
        f"Төлем жасау үшін:"
    )

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🏦 Kaspi арқылы төлеу", url=KASPI_LINK))
    markup.add(telebot.types.InlineKeyboardButton("💰 Қолма-қол төлем", callback_data="cash_payment"))

    bot.send_message(chat_id, summary, parse_mode="Markdown", reply_markup=markup)
    bot.send_message(ADMIN_ID, f"📥 Жаңа тапсырыс:\n👤 {data['name']}\n📞 {data['phone']}\n🍞 {data['quantity']} нан\n📦 {data['address']}\n💰 Сома: {total} т")

@bot.callback_query_handler(func=lambda call: call.data == "cash_payment")
def handle_cash_payment(call):
    bot.send_message(call.message.chat.id, "✅ Қолма-қол төлем таңдалды. Тапсырысыңыз өңделуде. Рақмет!", reply_markup=main_menu_keyboard())

@bot.message_handler(content_types=['document'])
def handle_pdf_check(message):
    chat_id = message.chat.id
    if not message.document.file_name.lower().endswith('.pdf'):
        return bot.send_message(chat_id, "⚠️ Тек PDF форматтағы чек қабылданады.")

    data = user_data.get(chat_id)
    if not data:
        return bot.send_message(chat_id, "Қате: тапсырыс табылмады.")

    caption = (
        f"📄 Клиенттен чек келді:\n"
        f"👤 {data.get('name')}\n"
        f"📞 {data.get('phone')}\n"
        f"🍞 {data.get('quantity')} нан\n"
        f"📦 {data.get('address')}\n"
        f"💰 {data.get('total')} т"
    )

    bot.send_message(chat_id, "✅ Төлем чегі қабылданды. Тапсырысыңыз өңделуде. Рақмет!", reply_markup=main_menu_keyboard())
    bot.send_document(ADMIN_ID, message.document.file_id, caption=caption)

# Flask қолданатындықтан, polling қажет емес
