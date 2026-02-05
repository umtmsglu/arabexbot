import os

import requests
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    raise RuntimeError("BOT_TOKEN bulunamadı. .env dosyasını kontrol edin.")

url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
response = requests.get(url, timeout=30)

if response.status_code == 200:
    print("✅ Webhook başarıyla silindi.")
else:
    print("❌ Webhook silinemedi:", response.text)
