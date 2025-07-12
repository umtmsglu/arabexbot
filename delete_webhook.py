import requests

BOT_TOKEN = '7709920480:AAGZVlaONRsP0iNEPWrix1J5iLJV7-oWtSM'

url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
response = requests.get(url)

if response.status_code == 200:
    print("✅ Webhook başarıyla silindi.")
else:
    print("❌ Webhook silinemedi:", response.text)
