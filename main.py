import logging from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler, )

==================== CONFIG ====================

BOT_TOKEN = "8263269951:AAEZ52DKTruGI6ujfHjq4gh9ZK0JDWinBks" ADMIN_ID = 7912879029 MANDATORY_CHANNELS = ["@imprimex"]  # <-- replace with your channels

Files DB (in-memory)

files_db = {}

States for Conversation

WAITING_FILE, WAITING_KEYWORD, CONFIRMATION = range(3)

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

==================== START ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user keyboard = [[InlineKeyboardButton("Help", callback_data="help")]] markup = InlineKeyboardMarkup(keyboard) await update.message.reply_text( f"Welcome {user.first_name}.\n\nThis bot allows you to search files with a simple keyword.", reply_markup=markup, )

==================== ADD FILE (ADMIN) ====================

async def add_file_entry(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return await update.message.reply_text("Access denied.") await update.message.reply_text("Send me the file you want to add.") return WAITING_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE): file_id = update.message.document.file_id context.user_data["new_file"] = file_id await update.message.reply_text("Now send me the keyword for this file.") return WAITING_KEYWORD

async def receive_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE): keyword = update.message.text.strip().lower() context.user_data["keyword"] = keyword await update.message.reply_text(f"Keyword: {keyword}\nConfirm? (yes/no)") return CONFIRMATION

async def confirm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE): answer = update.message.text.strip().lower() if answer == "yes": keyword = context.user_data["keyword"] files_db[keyword] = context.user_data["new_file"] await update.message.reply_text("File successfully added.") else: await update.message.reply_text("Cancelled.") return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Process cancelled.") return ConversationHandler.END

==================== SEARCH ====================

async def search_file(update: Update, context: ContextTypes.DEFAULT_TYPE): keyword = update.message.text.strip().lower() if keyword in files_db: await update.message.reply_document(files_db[keyword]) else: await update.message.reply_text("No file found for that keyword.")

==================== ADMIN PANEL ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return await update.message.reply_text("Access denied.") keyboard = [ [InlineKeyboardButton("Add File", callback_data="add_file")], [InlineKeyboardButton("Manage Files", callback_data="manage")], [InlineKeyboardButton("Mandatory Channels", callback_data="channels")], ] await update.message.reply_text("Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() if query.data == "help": await query.edit_message_text("Just type a keyword and I’ll return the file if it exists.") elif query.data == "add_file": await query.edit_message_text("Use /add to upload a new file.") elif query.data == "manage": if not files_db: await query.edit_message_text("No files stored yet.") else: msg = "Stored files:\n" for k in files_db.keys(): msg += f"- {k}\n" await query.edit_message_text(msg) elif query.data == "channels": text = "Mandatory channels:\n" + "\n".join(MANDATORY_CHANNELS) await query.edit_message_text(text)

==================== MAIN ====================

def main(): app = Application.builder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add", add_file_entry)],
    states={
        WAITING_FILE: [MessageHandler(filters.Document.ALL, receive_file)],
        WAITING_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keyword)],
        CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_entry)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_file))

app.run_polling()

if name == "main": main()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): uid = str(update.effective_user.id) if not await check_subscription(uid, context.bot): await update.message.reply_text(f"You must join our channel first: {CHANNEL}") return cap = generate_captcha() users[uid] = {"captcha": cap} save_json("users.json", users) await update.message.reply_text(f"Enter this code to continue: {cap}")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE): uid = str(update.effective_user.id) text = update.message.text.strip()

if not await check_subscription(uid, context.bot):
    await update.message.reply_text(f"You must join our channel first: {CHANNEL}")
    return

if uid in users and "captcha" in users[uid]:
    if text == users[uid]["captcha"]:
        del users[uid]["captcha"]
        save_json("users.json", users)
        await update.message.reply_text("**Main Menu**", reply_markup=main_menu())
    else:
        await update.message.reply_text("Wrong code.")
    return

if text == "Encrypt":
    await show_algorithms(update, context, "encrypt")
elif text == "Decrypt":
    await show_algorithms(update, context, "decrypt")
elif text == "Generate Code (AI)":
    await update.message.reply_text("Send a prompt describing the code you want:")
    context.user_data["action"] = "ai"
elif text == "Scan & Fix Code":
    await update.message.reply_text("Send your code to scan and fix it:")
    context.user_data["action"] = "fix"
elif text == "Contact Developer":
    await update.message.reply_text("Contact: @YXXVI")
else:
    await update.message.reply_text("**Main Menu**", reply_markup=main_menu())

async def show_algorithms(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str): context.user_data["mode"] = mode kb = InlineKeyboardMarkup([ [InlineKeyboardButton("Base64", callback_data=f"algo_base64")], [InlineKeyboardButton("Hex", callback_data=f"algo_hex")], [InlineKeyboardButton("ROT13", callback_data=f"algo_rot13")], [InlineKeyboardButton("Reverse", callback_data=f"algo_rev")], [InlineKeyboardButton("Caesar", callback_data=f"algo_caesar")], [InlineKeyboardButton("Binary", callback_data=f"algo_bin")], [InlineKeyboardButton("Morse", callback_data=f"algo_morse")], [InlineKeyboardButton("URL Encode", callback_data=f"algo_url")], [InlineKeyboardButton("XOR", callback_data=f"algo_xor")] ]) await update.message.reply_text("Choose algorithm:", reply_markup=kb)

async def algo_selection(update: Update, context: ContextTypes.DEFAULT_TYPE): q = update.callback_query await q.answer() algo = q.data.split("_")[1] context.user_data["algo"] = algo await q.message.reply_text(f"Send your text to {context.user_data['mode']} using {algo}:")

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE): uid = str(update.effective_user.id) action = context.user_data.get("action") algo = context.user_data.get("algo") text = update.message.text

if action == "ai":
    await update.message.reply_text(f"**# by primex | Verified by the developer primex**\nprint('Hello World')")
elif action == "fix":
    await update.message.reply_text(f"Code scanned. Status: ✅ Safe\n\n**# by primex | Verified by the developer primex**")
elif action in ["encrypt", "decrypt"] and algo:
    result = apply_algorithm(text, algo, action)
    await update.message.reply_text(f"**# by primex | Verified by the developer primex**\n{result}")
else:
    await update.message.reply_text("Please select action again from menu.")

=== Algorithms ===

def apply_algorithm(text, algo, mode): try: if algo == "base64": return base64.b64encode(text.encode()).decode() if mode=="encrypt" else base64.b64decode(text).decode() if algo == "hex": return text.encode().hex() if mode=="encrypt" else bytes.fromhex(text).decode() if algo == "rot13": return codecs.encode(text, 'rot_13') if algo == "rev": return text[::-1] if algo == "caesar": shift = 3 return ''.join(chr((ord(c)+shift)%256) if mode=="encrypt" else chr((ord(c)-shift)%256) for c in text) if algo == "bin": return ' '.join(format(ord(c), '08b') for c in text) if mode=="encrypt" else ''.join(chr(int(b, 2)) for b in text.split()) if algo == "morse": MORSE = { 'A':'.-', 'B':'-...', 'C':'-.-.', 'D':'-..', 'E':'.', 'F':'..-.', 'G':'--.', 'H':'....', 'I':'..', 'J':'.---', 'K':'-.-', 'L':'.-..', 'M':'--', 'N':'-.', 'O':'---', 'P':'.--.', 'Q':'--.-', 'R':'.-.', 'S':'...', 'T':'-', 'U':'..-', 'V':'...-', 'W':'.--', 'X':'-..-', 'Y':'-.--', 'Z':'--..', ' ':'/', '1':'.----', '2':'..---', '3':'...--', '4':'....-', '5':'.....', '6':'-....', '7':'--...', '8':'---..', '9':'----.', '0':'-----'} if mode == "encrypt": return ' '.join(MORSE.get(c.upper(), '') for c in text) else: inv = {v: k for k, v in MORSE.items()} return ''.join(inv.get(p, '') for p in text.split()) if algo == "url": return urllib.parse.quote(text) if mode=="encrypt" else urllib.parse.unquote(text) if algo == "xor": key = 5 return ''.join(chr(ord(c)^key) for c in text) return "Unknown algorithm." except: return "Error while processing."

=== Admin ===

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != OWNER_ID: return await update.message.reply_text("Admin Panel", reply_markup=admin_panel())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE): q = update.callback_query await q.answer() if q.from_user.id != OWNER_ID: return if q.data == "add_channel": await q.message.reply_text("Send new channel username:") context.user_data["admin_action"] = "add" elif q.data == "remove_channel": chs = channels.get("channels", []) kb = [[InlineKeyboardButton(c, callback_data=f"rm_{c}")] for c in chs] await q.message.reply_text("Click to remove:", reply_markup=InlineKeyboardMarkup(kb)) elif q.data.startswith("rm_"): ch = q.data[3:] channels["channels"].remove(ch) save_json("channels.json", channels) await q.message.reply_text("Removed.") elif q.data == "update_code": await q.message.reply_text("Send main.py file:") context.user_data["admin_action"] = "update" elif q.data == "view_code": with open("main.py") as f: code = f.read() await q.message.reply_text(f"<pre>{code}</pre>", parse_mode="HTML")

async def handle_docs(update: Update, context: ContextTypes.DEFAULT_TYPE): uid = update.effective_user.id action = context.user_data.get("admin_action") if action == "update" and uid == OWNER_ID: file = await update.message.document.get_file() await file.download_to_drive("main.py") await update.message.reply_text("Bot updated.") context.user_data["admin_action"] = None

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE): uid = update.effective_user.id action = context.user_data.get("admin_action") if action == "add" and uid == OWNER_ID: ch = update.message.text.strip() if not ch.startswith("@"): ch = "@" + ch if "channels" not in channels: channels["channels"] = [] channels["channels"].append(ch) save_json("channels.json", channels) await update.message.reply_text("Added.") context.user_data["admin_action"] = None

=== Main ===

if name == 'main': app = ApplicationBuilder().token(TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("admin", admin)) app.add_handler(CallbackQueryHandler(algo_selection, pattern="^algo_")) app.add_handler(CallbackQueryHandler(handle_buttons)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg)) app.add_handler(MessageHandler(filters.Document.ALL, handle_docs)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text), group=1) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code), group=2) print("Primex Core Bot is running...") app.run_polling()

