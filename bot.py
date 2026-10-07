import os
import json
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

OWNER_ID = 8768705030

DATA_FILE = Path("data.json")

publish_task = None
publish_lock = asyncio.Lock()

DEFAULT_DATA = {
    "groups": {},
    "posts": {},
    "next_post_id": 1,
    "auto": {
        "enabled": False,
        "interval": 3600,
        "current_post": 1
    }
}


def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("groups", {})
        data.setdefault("posts", {})
        data.setdefault("next_post_id", 1)
        data.setdefault("auto", {})
        data["auto"].setdefault("enabled", False)
        data["auto"].setdefault("interval", 3600)
        data["auto"].setdefault("current_post", 1)

        return data

    except Exception:
        return DEFAULT_DATA.copy()


def save_data(data):
    temp_file = Path("data.tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    temp_file.replace(DATA_FILE)


data = load_data()


def is_owner(update: Update):
    return (
        update.effective_user
        and update.effective_user.id == OWNER_ID
    )


async def owner_only(update: Update):
    if not is_owner(update):
        if update.message:
            await update.message.reply_text(
                "❌ هذا الأمر مخصص لمالك البوت فقط."
            )
        return False

    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if is_owner(update):
        await update.message.reply_text(
            "🤖 أهلاً بك في بوت النشر التلقائي.\n\n"
            "استخدم /help لعرض جميع الأوامر."
        )
    else:
        await update.message.reply_text(
            "🤖 أهلاً بك.\n"
            "هذا البوت مخصص للنشر التلقائي."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    text = """
📋 لوحة تحكم بوت النشر

👥 المجموعات:

/addgroup
إضافة المجموعة الحالية إلى قائمة النشر.

/groups
عرض المجموعات.

/removegroup ID
حذف مجموعة.

📝 المنشورات:

/savepost
حفظ رسالة كمنشور.

/posts
عرض المنشورات.

/deletepost ID
حذف منشور.

📢 النشر:

/publish ID
نشر منشور فوراً.

/autostart MINUTES
تشغيل النشر التلقائي.

/autostop
إيقاف النشر التلقائي.

/status
عرض حالة البوت.

/id
عرض Telegram ID.
"""

    await update.message.reply_text(text)


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"🆔 Telegram ID:\n\n{update.effective_user.id}"
    )


async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(
            "❌ استخدم /addgroup داخل المجموعة."
        )
        return

    chat_id = str(chat.id)

    data["groups"][chat_id] = {
        "title": chat.title or "بدون اسم"
    }

    save_data(data)

    await update.message.reply_text(
        f"✅ تمت إضافة المجموعة.\n\n"
        f"📌 {chat.title}\n"
        f"🆔 {chat.id}"
               )async def groups(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    if not data["groups"]:
        await update.message.reply_text(
            "📭 لا توجد مجموعات مضافة حالياً."
        )
        return

    text = "👥 مجموعات النشر:\n\n"

    for i, (chat_id, info) in enumerate(
        data["groups"].items(), start=1
    ):
        text += (
            f"{i}. {info.get('title', 'بدون اسم')}\n"
            f"🆔 `{chat_id}`\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )


async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/removegroup ID"
        )
        return

    chat_id = context.args[0]

    if chat_id not in data["groups"]:
        await update.message.reply_text(
            "❌ هذه المجموعة غير موجودة في القائمة."
        )
        return

    name = data["groups"][chat_id].get(
        "title",
        "المجموعة"
    )

    del data["groups"][chat_id]

    save_data(data)

    await update.message.reply_text(
        f"✅ تم حذف المجموعة:\n{name}"
    )


async def save_post(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لازم تستخدم /savepost كرد على الرسالة "
            "التي تريد حفظها كمنشور."
        )
        return

    source = update.message.reply_to_message

    post_id = str(data["next_post_id"])

    data["next_post_id"] += 1

    data["posts"][post_id] = {
        "chat_id": source.chat_id,
        "message_id": source.message_id
    }

    save_data(data)

    await update.message.reply_text(
        f"✅ تم حفظ المنشور بنجاح.\n\n"
        f"📝 رقم المنشور: {post_id}\n\n"
        f"استخدم:\n"
        f"/publish {post_id}\n"
        f"للنشر فوراً."
    )


async def posts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    if not data["posts"]:
        await update.message.reply_text(
            "📭 لا توجد منشورات محفوظة."
        )
        return

    text = "📝 المنشورات المحفوظة:\n\n"

    for post_id in sorted(
        data["posts"],
        key=lambda x: int(x)
    ):
        text += f"📌 منشور رقم: {post_id}\n"

    await update.message.reply_text(text)


async def delete_post(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/deletepost ID"
        )
        return

    post_id = context.args[0]

    if post_id not in data["posts"]:
        await update.message.reply_text(
            "❌ المنشور غير موجود."
        )
        return

    del data["posts"][post_id]

    save_data(data)

    await update.message.reply_text(
        f"🗑️ تم حذف المنشور رقم {post_id}."
    )


async def publish_post(bot, post_id):

    if post_id not in data["posts"]:
        return 0, 0

    if not data["groups"]:
        return 0, 0

    post = data["posts"][post_id]

    success = 0
    failed = 0

    for chat_id in list(data["groups"].keys()):

        try:

            await bot.copy_message(
                chat_id=int(chat_id),
                from_chat_id=post["chat_id"],
                message_id=post["message_id"]
            )

            success += 1

            await asyncio.sleep(2)

        except Exception as e:

            failed += 1

            print(
                f"❌ Failed to publish to {chat_id}: {e}"
            )

    return success, failedasync def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/publish ID"
        )
        return

    post_id = context.args[0]

    if post_id not in data["posts"]:
        await update.message.reply_text(
            "❌ المنشور غير موجود."
        )
        return

    if not data["groups"]:
        await update.message.reply_text(
            "❌ لا توجد مجموعات مضافة."
        )
        return

    await update.message.reply_text(
        f"📢 جاري نشر المنشور رقم {post_id}..."
    )

    success, failed = await publish_post(
        context.bot,
        post_id
    )

    await update.message.reply_text(
        f"✅ انتهى النشر.\n\n"
        f"نجح: {success}\n"
        f"فشل: {failed}"
    )


async def automatic_publisher(bot):

    while data["auto"]["enabled"]:

        try:

            async with publish_lock:

                post_ids = sorted(
                    data["posts"].keys(),
                    key=lambda x: int(x)
                )

                if not post_ids:
                    print("📭 لا توجد منشورات للنشر.")

                elif data["groups"]:

                    current = data["auto"]["current_post"]

                    if current > len(post_ids):
                        current = 1

                    post_id = post_ids[current - 1]

                    print(
                        f"📢 Auto publishing post {post_id}"
                    )

                    await publish_post(
                        bot,
                        post_id
                    )

                    current += 1

                    if current > len(post_ids):
                        current = 1

                    data["auto"]["current_post"] = current

                    save_data(data)

        except Exception as e:

            print(
                f"❌ Auto publisher error: {e}"
            )

        interval = data["auto"]["interval"]

        await asyncio.sleep(interval)


async def autostart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global publish_task

    if not await owner_only(update):
        return

    if not data["posts"]:
        await update.message.reply_text(
            "❌ ما في منشورات محفوظة."
        )
        return

    if not data["groups"]:
        await update.message.reply_text(
            "❌ ما في مجموعات مضافة."
        )
        return

    if not context.args:

        await update.message.reply_text(
            "الاستخدام:\n\n"
            "/autostart MINUTES\n\n"
            "مثال:\n"
            "/autostart 60\n\n"
            "يعني منشور جديد كل ساعة."
        )

        return

    try:

        minutes = float(context.args[0])

        if minutes < 1:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ اكتب مدة صحيحة بالدقائق.\n\n"
            "مثال:\n"
            "/autostart 30"
        )

        return

    data["auto"]["enabled"] = True
    data["auto"]["interval"] = int(minutes * 60)

    if data["auto"]["current_post"] < 1:
        data["auto"]["current_post"] = 1

    save_data(data)

    if publish_task is None or publish_task.done():

        publish_task = asyncio.create_task(
            automatic_publisher(context.bot)
        )

    await update.message.reply_text(
        f"🚀 تم تشغيل النشر التلقائي.\n\n"
        f"⏰ كل {minutes:g} دقيقة\n"
        f"📝 عدد المنشورات: {len(data['posts'])}\n"
        f"👥 عدد المجموعات: {len(data['groups'])}"
    )


async def autostop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    data["auto"]["enabled"] = False

    save_data(data)

    await update.message.reply_text(
        "⏸️ تم إيقاف النشر التلقائي."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await owner_only(update):
        return

    enabled = data["auto"]["enabled"]

    if enabled:

        minutes = data["auto"]["interval"] / 60

        auto_status = (
            f"🟢 يعمل\n"
            f"⏰ كل {minutes:g} دقيقة"
        )

    else:

        auto_status = "🔴 متوقف"

    await update.message.reply_text(
        "📊 حالة البوت\n\n"
        f"👥 المجموعات: {len(data['groups'])}\n"
        f"📝 المنشورات: {len(data['posts'])}\n\n"
        f"🤖 النشر التلقائي:\n{auto_status}"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🏓 Pong!\n"
        "✅ البوت يعمل."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    print(
        f"❌ Error: {context.error}"
    )def main():

    if not TOKEN:
        raise ValueError(
            "❌ TELEGRAM_BOT_TOKEN غير موجود."
        )

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("id", get_id)
    )

    application.add_handler(
        CommandHandler("ping", ping)
    )

    application.add_handler(
        CommandHandler("addgroup", add_group)
    )

    application.add_handler(
        CommandHandler("groups", groups)
    )

    application.add_handler(
        CommandHandler("removegroup", remove_group)
    )

    application.add_handler(
        CommandHandler("savepost", save_post)
    )

    application.add_handler(
        CommandHandler("posts", posts)
    )

    application.add_handler(
        CommandHandler("deletepost", delete_post)
    )

    application.add_handler(
        CommandHandler("publish", publish)
    )

    application.add_handler(
        CommandHandler("autostart", autostart)
    )

    application.add_handler(
        CommandHandler("autostop", autostop)
    )

    application.add_handler(
        CommandHandler("status", status)
    )

    application.add_error_handler(
        error_handler
    )

    print("🤖 Auto Publisher Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
