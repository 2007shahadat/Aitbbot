import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I’m your AI Chat Bot (polling).")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    payload = {"contents":[{"parts":[{"text": user_message}]}]}
    headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}
    try:
        res = requests.post(GEMINI_API_URL, headers=headers, json=payload).json()
        ai_reply = res["candidates"][0]["content"]["parts"][0]["text"]
        await update.message.reply_text(ai_reply)
    except Exception as e:
        await update.message.reply_text("⚠️ Error contacting AI.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("✅ Running locally (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
