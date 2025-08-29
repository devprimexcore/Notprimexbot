import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ==================== CONFIG ====================
BOT_TOKEN = "8263269951:AAEZ52DKTruGI6ujfHjq4gh9ZK0JDWinBks"
ADMIN_ID = 7912879029
MANDATORY_CHANNELS = ["@imprimex"]

# ==================== IN-MEMORY DB ====================
files_db = {}

# ==================== CONVERSATION STATES ====================
WAITING_FILE, WAITING_KEYWORD, CONFIRMATION = range(3)

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("Help", callback_data="help")]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Welcome {user.first_name}!\n\nThis bot allows you to search files using keywords.",
        reply_markup=markup
    )

# ==================== ADD FILE (ADMIN) ====================
async def add_file_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Access denied.")
    await update.message.reply_text("📎 Send me the file you want to add.")
    return WAITING_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        return await update.message.reply_text("❌ Please send a valid file.")
    context.user_data["new_file"] = update.message.document.file_id
    await update.message.reply_text("📝 Now send me the keyword for this file.")
    return WAITING_KEYWORD

async def receive_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip().lower()
    if not keyword:
        return await update.message.reply_text("❌ Keyword cannot be empty.")
    context.user_data["keyword"] = keyword
    await update.message.reply_text(f"🔑 Keyword: {keyword}\nConfirm? (yes/no)")
    return CONFIRMATION

async def confirm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer == "yes":
        keyword = context.user_data["keyword"]
        files_db[keyword] = context.user_data["new_file"]
        await update.message.reply_text("✅ File successfully added.")
    else:
        await update.message.reply_text("❌ Process cancelled.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Process cancelled.")
    return ConversationHandler.END

# ==================== SEARCH ====================
async def search_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return  # ignore commands
    user = update.effective_user
    # Check mandatory channels
    for channel in MANDATORY_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user.id)
            if member.status in ["left", "kicked"]:
                return await update.message.reply_text(
                    f"⚠️ You must join {channel} to use this bot."
                )
        except:
            continue
    keyword = update.message.text.strip().lower()
    if keyword in files_db:
        await update.message.reply_document(files_db[keyword])
    else:
        await update.message.reply_text("❌ No file found for that keyword.")

# ==================== ADMIN PANEL ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Access denied.")
    keyboard = [
        [InlineKeyboardButton("➕ Add File", callback_data="add_file")],
        [InlineKeyboardButton("🗂 Manage Files", callback_data="manage")],
        [InlineKeyboardButton("📌 Mandatory Channels", callback_data="channels")],
    ]
    await update.message.reply_text("🛠 Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help":
        await query.edit_message_text("💡 Just type a keyword and I’ll return the file if it exists.")
    elif data == "add_file":
        await query.edit_message_text("Use /add to upload a new file.")
    elif data == "manage":
        if not files_db:
            await query.edit_message_text("📂 No files stored yet.")
        else:
            msg = "📂 Stored files:\n" + "\n".join(f"- {k}" for k in files_db.keys())
            await query.edit_message_text(msg)
    elif data == "channels":
        text = "📌 Mandatory channels:\n" + "\n".join(MANDATORY_CHANNELS)
        await query.edit_message_text(text)

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for /add
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_file_entry)],
        states={
            WAITING_FILE: [MessageHandler(filters.Document.ALL, receive_file)],
            WAITING_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keyword)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_entry)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_file))  # last

    app.run_polling()

if __name__ == "__main__":
    main()
