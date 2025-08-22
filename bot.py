import os
import json
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ---------- Config from Environment ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("telegram-gemini-bot")

# ---------- Helpers ----------
def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        # Return explicit message if key missing
        return "⚠️ Server error: GEMINI_API_KEY missing. Please set it in Render Environment."

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    try:
        resp = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=payload,
            timeout=20
        )
        text_body = resp.text  # keep for logs
        if resp.status_code != 200:
            logger.error("Gemini HTTP %s: %s", resp.status_code, text_body[:2000])
            return f"⚠️ AI API error ({resp.status_code})."

        data = resp.json()
        # Happy path
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            # Log full response for debugging
            logger.warning("Gemini no candidates/parts. Full: %s", json.dumps(data)[:2000])
            # If promptFeedback or safety blocks exist
            if "promptFeedback" in data:
                pf = data["promptFeedback"]
                return "⚠️ AI couldn’t answer this prompt (safety or policy). Try rephrasing."
            if "error" in data:
                err = data["error"]
                return f"⚠️ AI error: {err.get('message','Unknown')}"

            return "⚠️ AI returned an unexpected response. Please try again."

    except requests.Timeout:
        logger.exception("Gemini request timed out")
        return "⚠️ AI timeout. Please try again."
    except Exception:
        logger.exception("Gemini request failed")
        return "⚠️ Error contacting AI."

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Hi! I’m your AI bot.\n"
        "Send me any message and I’ll reply using Gemini.\n"
        "Tip: Try `Write an HTML code for a calculator`"
    )

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok_env = bool(BOT_TOKEN) and bool(GEMINI_API_KEY)
    await update.message.reply_text(
        f"✅ Health check\nBOT_TOKEN: {'set' if BOT_TOKEN else 'missing'}\n"
        f"GEMINI_API_KEY: {'set' if GEMINI_API_KEY else 'missing'}"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    logger.info("User %s: %s", update.effective_user.id, user_text[:200])
    reply = call_gemini(user_text)
    await update.message.reply_text(reply)

# ---------- Main ----------
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment.")
        raise SystemExit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("✅ Bot is running with polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
