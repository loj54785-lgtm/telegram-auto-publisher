import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================
# الإعدادات
# =========================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ضع Telegram ID الخاص بك هنا لاحقاً
OWNER_ID = 0


# =========================
# التحقق من المالك
# =========================

def is_owner(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == OWNER_ID


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 أهلاً بك في بوت النشر التلقائي!\n\n"
        "استخدم /help لمعرفة الأوامر."
    )


# =========================
# /help
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 أوامر البوت:\n\n"
        "/start - تشغيل البوت\n"
        "/help - المساعدة\n"
        "/id - معرفة Telegram ID الخاص بك\n"
        "/test - اختبار البوت"
    )


# =========================
# /id
# =========================

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        f"🆔 Telegram ID الخاص بك هو:\n\n"
        f"`{user_id}`",
        parse_mode="Markdown"
    )


# =========================
# /test
# =========================

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text(
            "❌ هذا الأمر مخصص للمالك فقط."
        )
        return

    await update.message.reply_text(
        "✅ البوت يعمل بشكل صحيح."
    )


# =========================
# تشغيل البوت
# =========================

def main():
    if not TOKEN:
        raise ValueError(
            "❌ لم يتم العثور على TELEGRAM_BOT_TOKEN"
        )

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", get_id))
    application.add_handler(CommandHandler("test", test))

    print("🤖 Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
