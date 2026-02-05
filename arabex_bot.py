import json
import os
from datetime import datetime
from threading import Lock

import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_ENV = os.getenv("ADMIN_ID")
DATA_FILE = os.getenv("DATA_FILE", "game_data.json")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN bulunamadı. .env dosyasını kontrol et.")

try:
    ADMIN_ID = int(ADMIN_ID_ENV) if ADMIN_ID_ENV else None
except ValueError as exc:
    raise RuntimeError("ADMIN_ID sayısal bir değer olmalı.") from exc

bot = telebot.TeleBot(BOT_TOKEN)
state_lock = Lock()

POINTS_EXACT = 3
POINTS_DIFF = 2
POINTS_OUTCOME = 1


def default_state():
    return {
        "next_match_id": 1,
        "matches": {},
        "predictions": {},
        "users": {},
    }


def load_state():
    if not os.path.exists(DATA_FILE):
        return default_state()

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


state = load_state()


def is_admin(user_id):
    return ADMIN_ID is not None and user_id == ADMIN_ID


def parse_match_time(raw_date):
    return datetime.strptime(raw_date.strip(), "%Y-%m-%d %H:%M")


def format_match_line(match_id, match_data):
    kickoff = datetime.fromisoformat(match_data["kickoff"])
    status_emoji = "🟢" if match_data["status"] == "open" else "🔒"
    return (
        f"{status_emoji} #{match_id} - {match_data['home']} vs {match_data['away']}"
        f" | Başlangıç: {kickoff.strftime('%d.%m.%Y %H:%M')}"
    )


def evaluate_prediction(pred_home, pred_away, real_home, real_away):
    if pred_home == real_home and pred_away == real_away:
        return POINTS_EXACT

    pred_diff = pred_home - pred_away
    real_diff = real_home - real_away

    if pred_diff == real_diff:
        return POINTS_DIFF

    pred_outcome = 1 if pred_diff > 0 else -1 if pred_diff < 0 else 0
    real_outcome = 1 if real_diff > 0 else -1 if real_diff < 0 else 0

    if pred_outcome == real_outcome:
        return POINTS_OUTCOME

    return 0


def upsert_user(user):
    user_id = str(user.id)
    if user_id not in state["users"]:
        state["users"][user_id] = {
            "username": user.username or "",
            "first_name": user.first_name or "",
            "points": 0,
        }
    else:
        if user.username:
            state["users"][user_id]["username"] = user.username
        if user.first_name:
            state["users"][user_id]["first_name"] = user.first_name


def display_name(user_data, user_id):
    if user_data.get("username"):
        return f"@{user_data['username']}"
    if user_data.get("first_name"):
        return user_data["first_name"]
    return f"Kullanıcı {user_id}"


@bot.message_handler(commands=["start"])
def start(message):
    with state_lock:
        upsert_user(message.from_user)
        save_state(state)

    text = (
        "⚽️ *Futbol Tahmin Oyununa Hoş Geldin!*\n\n"
        "Bu botta maç skor tahmini yaparak puan toplarsın.\n"
        "Sezon sonunda liderlere ödül verilebilir.\n\n"
        "Komutlar:\n"
        "• `/maclar` - Açık maçları gösterir\n"
        "• `/tahmin <maç_id> <ev_skor> <dep_skor>`\n"
        "• `/puan_durumu` - Liderlik tablosu\n"
        "• `/yardim` - Tüm komutlar"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["yardim"])
def help_command(message):
    text = (
        "📘 *Komut Listesi*\n\n"
        "Kullanıcı komutları:\n"
        "• `/maclar`\n"
        "• `/tahmin <maç_id> <ev_skor> <dep_skor>`\n"
        "• `/puan_durumu`\n"
        "• `/oduller`\n\n"
        "Admin komutları:\n"
        "• `/mac_ekle EvTakım|Deplasman|YYYY-MM-DD HH:MM`\n"
        "• `/sonuc_gir <maç_id> <ev_skor> <dep_skor>`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["mac_ekle"])
def add_match(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Bu komut sadece admin için.")
        return

    payload = message.text.replace("/mac_ekle", "", 1).strip()
    parts = [part.strip() for part in payload.split("|")]
    if len(parts) != 3:
        bot.reply_to(message, "❗ Format: /mac_ekle EvTakım|Deplasman|YYYY-MM-DD HH:MM")
        return

    home, away, kickoff_raw = parts
    try:
        kickoff = parse_match_time(kickoff_raw)
    except ValueError:
        bot.reply_to(message, "❗ Tarih formatı hatalı. Örn: 2026-02-05 20:45")
        return

    with state_lock:
        match_id = str(state["next_match_id"])
        state["next_match_id"] += 1
        state["matches"][match_id] = {
            "home": home,
            "away": away,
            "kickoff": kickoff.isoformat(),
            "status": "open",
            "result": None,
        }
        save_state(state)

    bot.reply_to(message, f"✅ Maç eklendi: #{match_id} {home} vs {away}")


@bot.message_handler(commands=["maclar"])
def list_matches(message):
    with state_lock:
        open_matches = [
            (match_id, data)
            for match_id, data in state["matches"].items()
            if data["status"] == "open"
        ]

    if not open_matches:
        bot.send_message(message.chat.id, "Şu anda açık maç yok.")
        return

    lines = ["🗓️ *Açık Maçlar*"]
    for match_id, data in open_matches:
        lines.append(format_match_line(match_id, data))

    lines.append("\nTahmin için: `/tahmin <maç_id> <ev_skor> <dep_skor>`")
    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["tahmin"])
def predict(message):
    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(message, "❗ Kullanım: /tahmin <maç_id> <ev_skor> <dep_skor>")
        return

    _, match_id, pred_home_raw, pred_away_raw = args

    try:
        pred_home = int(pred_home_raw)
        pred_away = int(pred_away_raw)
        if pred_home < 0 or pred_away < 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❗ Skorlar 0 veya pozitif tam sayı olmalı.")
        return

    with state_lock:
        match_data = state["matches"].get(match_id)
        if not match_data:
            bot.reply_to(message, "❌ Bu ID ile maç bulunamadı.")
            return

        if match_data["status"] != "open":
            bot.reply_to(message, "⏳ Bu maç tahmine kapalı.")
            return

        kickoff = datetime.fromisoformat(match_data["kickoff"])
        if datetime.now() >= kickoff:
            bot.reply_to(message, "⛔ Maç başladı, artık tahmin alınmıyor.")
            return

        upsert_user(message.from_user)
        user_id = str(message.from_user.id)
        if user_id not in state["predictions"]:
            state["predictions"][user_id] = {}

        state["predictions"][user_id][match_id] = {
            "home": pred_home,
            "away": pred_away,
            "created_at": datetime.now().isoformat(),
        }
        save_state(state)

    bot.reply_to(
        message,
        f"✅ Tahmin kaydedildi: #{match_id} için {pred_home}-{pred_away}",
    )


@bot.message_handler(commands=["sonuc_gir"])
def enter_result(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Bu komut sadece admin için.")
        return

    args = message.text.split()
    if len(args) != 4:
        bot.reply_to(message, "❗ Kullanım: /sonuc_gir <maç_id> <ev_skor> <dep_skor>")
        return

    _, match_id, home_raw, away_raw = args
    try:
        home_score = int(home_raw)
        away_score = int(away_raw)
        if home_score < 0 or away_score < 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❗ Skorlar 0 veya pozitif tam sayı olmalı.")
        return

    awarded = []
    with state_lock:
        match_data = state["matches"].get(match_id)
        if not match_data:
            bot.reply_to(message, "❌ Maç bulunamadı.")
            return

        if match_data["status"] == "closed":
            bot.reply_to(message, "ℹ️ Bu maç zaten kapatılmış.")
            return

        match_data["status"] = "closed"
        match_data["result"] = {
            "home": home_score,
            "away": away_score,
        }

        for user_id, user_predictions in state["predictions"].items():
            if match_id not in user_predictions:
                continue

            prediction = user_predictions[match_id]
            gained = evaluate_prediction(
                prediction["home"],
                prediction["away"],
                home_score,
                away_score,
            )
            state["users"].setdefault(user_id, {"username": "", "first_name": "", "points": 0})
            state["users"][user_id]["points"] = state["users"][user_id].get("points", 0) + gained
            awarded.append((user_id, gained, prediction))

        save_state(state)

    summary = [f"✅ #{match_id} sonucu girildi: {home_score}-{away_score}"]
    if awarded:
        summary.append("\nPuan dağılımı:")
        for user_id, gained, prediction in awarded:
            name = display_name(state["users"].get(user_id, {}), user_id)
            summary.append(f"• {name}: {prediction['home']}-{prediction['away']} ➜ +{gained}")
    else:
        summary.append("\nBu maça tahmin yapan kullanıcı yok.")

    bot.send_message(message.chat.id, "\n".join(summary))


@bot.message_handler(commands=["puan_durumu"])
def leaderboard(message):
    with state_lock:
        ranking = sorted(
            state["users"].items(),
            key=lambda item: item[1].get("points", 0),
            reverse=True,
        )

    if not ranking:
        bot.send_message(message.chat.id, "Henüz puan tablosu oluşmadı.")
        return

    lines = ["🏆 *Puan Durumu*"]
    for index, (user_id, user_data) in enumerate(ranking, start=1):
        lines.append(f"{index}. {display_name(user_data, user_id)} — {user_data.get('points', 0)} puan")

    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["oduller"])
def rewards_info(message):
    text = (
        "🎁 *Ödül Önerisi*\n\n"
        "Haftalık veya aylık olarak ilk 3 kullanıcıya ödül verilebilir:\n"
        "1) 🥇 1. - Özel premium üyelik\n"
        "2) 🥈 2. - Hediye kupon\n"
        "3) 🥉 3. - Sürpriz ödül\n\n"
        "Ödül sistemi organizatör tarafından güncellenebilir."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


print("🤖 Bot çalışıyor...")
bot.infinity_polling(skip_pending=True)
