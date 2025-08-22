import os
import json
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_CANDIDATES = [
    "gemini-2.0-flash",      # চেষ্টা ১
    "gemini-1.5-flash"       # fallback
]

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("tg-gemini")

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ Server error: GEMINI_API_KEY missing on server."

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

    last_error = None

    for model in MODEL_CANDIDATES:
        url = BASE_URL.format(model=model)
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code != 200:
                # Save error text for debugging
                last_error = f"HTTP {resp.status_code}: {resp.text[:800]}"
                log.error("Gemini %s failed: %s", model, last_error)
                continue

            data = resp.json()
            # Happy path
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                # Extract detailed error if present
                err_fragments = []
                if "error" in data:
                    err = data["error"]
                    err_fragments.append(f"status={err.get('status')}")
                    err_fragments.append(f"code={err.get('code')}")
                    err_fragments.append(f"message={err.get('message')}")
                if "promptFeedback" in data:
                    err_fragments.append("promptFeedback present (safety/policy).")
                dbg = "; ".join(x for x in err_fragments if x)
                last_error = dbg or json.dumps(data)[:800]
                log.warning("Gemini %s unexpected shape: %s", model, last_error)
                continue

        except requests.Timeout:
            last_error = "Timeout while contacting Gemini."
            log.exception(last_error)
            continue
        except Exception as e:
            last_error = f"Exception: {repr(e)}"
            log.exception("Gemini request exception")
            continue

    # If all models failed:
    return f"⚠️ AI call failed.\nDetails: {last_error or 'Unknown error'}"

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Hi! Send me any message and I’ll answer with Gemini.\n"
        "Try: Write a web view HTML code."
    )

async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"BOT_TOKEN: {'set' if BOT_TOKEN else 'missing'}\n"
        f"GEMINI_API_KEY: {'set' if GEMINI_API_KEY else 'missing'}"
    )

async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = call_gemini("Reply with only the text: OK")
    await update.message.reply_text(f"Test result:\n{reply}")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    log.info("User %s: %s", update.effective_user.id, user_text[:200])
    reply = call_gemini(user_text)
    await update.message.reply_text(reply)

def main():
    if not BOT_TOKEN:
        log.error("BOT_TOKEN is missing.")
        raise SystemExit(1)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("✅ Bot running (polling)…")
    app.run_polling()

if __name__ == "__main__":
    main()