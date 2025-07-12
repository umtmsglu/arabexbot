import telebot
from datetime import datetime

BOT_TOKEN = 'BOT_TOKEN'
CHANNEL_USERNAME = '@arabexilan'
ADMIN_ID = 1081862641  # @haykigrafik

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
ilan_id = 1

# /start komutu
@bot.message_handler(commands=['start'])
def send_welcome(message):
    global ilan_id
    user_data[message.chat.id] = {'ilan_id': ilan_id, 'user_id': message.chat.id}
    ilan_id += 1
    bot.send_message(message.chat.id, "🚗 Araç markasını yaz (örn: Volkswagen):")

# /yardim komutu
@bot.message_handler(commands=['yardim'])
def send_help(message):
    help_text = (
        "📋 *Arabex İlan Botu Yardım*\n\n"
        "🔹 `/start` yazarak yeni bir ilan oluşturmaya başlayabilirsin.\n"
        "🔹 Sırasıyla:\n"
        "• Marka\n"
        "• Model\n"
        "• Yıl\n"
        "• Fiyat\n"
        "• Kilometre\n"
        "• Şanzıman\n"
        "• Yakıt\n"
        "• Renk\n"
        "• Telefon\n"
        "• Açıklama\n"
        "• Fotoğraf\n\n"
        "🔸 İlanın admin onayından sonra @arabexilan kanalında paylaşılır.\n"
        "🛑 Yardım için: @haykigrafik"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Marka ve model ayrı
@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'marka' not in user_data[msg.chat.id])
def marka(message):
    user_data[message.chat.id]['marka'] = message.text
    bot.send_message(message.chat.id, "📄 Araç modelini yaz (örn: Passat 1.6 TDI Comfortline):")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'model' not in user_data[msg.chat.id])
def model(message):
    user_data[message.chat.id]['model'] = message.text
    bot.send_message(message.chat.id, "📆 Araç yılı nedir?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'yil' not in user_data[msg.chat.id])
def yil(message):
    user_data[message.chat.id]['yil'] = message.text
    bot.send_message(message.chat.id, "💰 Fiyat nedir?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'fiyat' not in user_data[msg.chat.id])
def fiyat(message):
    user_data[message.chat.id]['fiyat'] = message.text
    bot.send_message(message.chat.id, "🛣️ Kilometre nedir?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'km' not in user_data[msg.chat.id])
def km(message):
    user_data[message.chat.id]['km'] = message.text
    bot.send_message(message.chat.id, "⚙️ Şanzıman türü?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'sanziman' not in user_data[msg.chat.id])
def sanziman(message):
    user_data[message.chat.id]['sanziman'] = message.text
    bot.send_message(message.chat.id, "⛽️ Yakıt türü?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'yakit' not in user_data[msg.chat.id])
def yakit(message):
    user_data[message.chat.id]['yakit'] = message.text
    bot.send_message(message.chat.id, "🎨 Renk?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'renk' not in user_data[msg.chat.id])
def renk(message):
    user_data[message.chat.id]['renk'] = message.text
    bot.send_message(message.chat.id, "📞 Telefon numarası?")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'telefon' not in user_data[msg.chat.id])
def telefon(message):
    user_data[message.chat.id]['telefon'] = message.text
    bot.send_message(message.chat.id, "📝 Araç hakkında kısa açıklama (isteğe bağlı):")

@bot.message_handler(func=lambda msg: msg.chat.id in user_data and 'aciklama' not in user_data[msg.chat.id])
def aciklama(message):
    user_data[message.chat.id]['aciklama'] = message.text
    bot.send_message(message.chat.id, "📸 Araç fotoğrafını gönder (1 adet):")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id not in user_data or 'foto' in user_data[message.chat.id]:
        return

    data = user_data[message.chat.id]
    data['foto'] = message.photo[-1].file_id
    data['username'] = f"@{message.from_user.username}" if message.from_user.username else "Yok"
    data['chat_id'] = message.chat.id

    now = datetime.now().strftime("%H:%M - %d.%m.%Y")

    caption = f"""
📋 İlan ID: #{data['ilan_id']}
📅 İlan Tarihi: {now}

🚗 Marka: {data['marka']} {data['model']} ({data['yil']})
💰 Fiyat: {data['fiyat']}
🛣️ Kilometre: {data['km']}
⚙️ Şanzıman: {data['sanziman']}
⛽️ Yakıt: {data['yakit']}
🎨 Renk: {data['renk']}
📞 Telefon: {data['telefon']}

📝 Açıklama: {data['aciklama']}

👤 Paylaşan: {data['username']}
"""

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ Onayla", callback_data=f"onayla_{data['chat_id']}"),
        telebot.types.InlineKeyboardButton("❌ Reddet", callback_data=f"reddet_{data['chat_id']}")
    )

    bot.send_photo(chat_id=ADMIN_ID, photo=data['foto'], caption=caption.strip(), reply_markup=markup)
    bot.send_message(message.chat.id, "✅ İlan gönderildi. Admin onayı bekleniyor...")

# Admin onay/ret işlemleri
@bot.callback_query_handler(func=lambda call: call.data.startswith("onayla_") or call.data.startswith("reddet_"))
def callback(call):
    action, target_chat_id = call.data.split("_")
    target_chat_id = int(target_chat_id)
    data = user_data.get(target_chat_id)

    if not data:
        bot.answer_callback_query(call.id, "İlan verisi bulunamadı.")
        return

    now = datetime.now().strftime("%H:%M - %d.%m.%Y")

    caption = f"""
📋 İlan ID: #{data['ilan_id']}
📅 İlan Tarihi: {now}

🚗 Marka: {data['marka']} {data['model']} ({data['yil']})
💰 Fiyat: {data['fiyat']}
🛣️ Kilometre: {data['km']}
⚙️ Şanzıman: {data['sanziman']}
⛽️ Yakıt: {data['yakit']}
🎨 Renk: {data['renk']}
📞 Telefon: {data['telefon']}

📝 Açıklama: {data['aciklama']}

👤 Paylaşan: {data['username']}
"""

    if action == "onayla":
        bot.send_photo(chat_id=CHANNEL_USERNAME, photo=data['foto'], caption=caption.strip())
        bot.send_message(chat_id=target_chat_id, text="✅ İlanın onaylandı ve @arabexilan kanalında yayınlandı.")
    else:
        bot.send_message(chat_id=target_chat_id, text="❌ İlanın reddedildi.")

    del user_data[target_chat_id]
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    bot.answer_callback_query(call.id)

# Botu başlat
bot.polling()
