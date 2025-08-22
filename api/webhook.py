import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@app.route("/api/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]

        payload = {"contents":[{"parts":[{"text": user_message}]}]}
        headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}

        try:
            res = requests.post(GEMINI_API_URL, headers=headers, json=payload).json()
            ai_reply = res["candidates"][0]["content"]["parts"][0]["text"]
        except:
            ai_reply = "⚠️ AI Error."

        send_message(chat_id, ai_reply)

    return {"ok": True}
