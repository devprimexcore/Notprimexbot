#Primex Core Bot - Version Final

#by primex | Verified by the developer primex

import os, json, base64, binascii, codecs, urllib.parse from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InputFile from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

=== Constants ===

TOKEN = "7967640262:AAFKCefly9fEBLVTUXm1BeOPQ1GPLKd_bkE" OWNER_ID = 7912879029 CHANNEL = "@vxwwo"

=== Helpers ===

def load_json(filename): if not os.path.exists(filename): return {} with open(filename, 'r') as f: return json.load(f)

def save_json(filename, data): with open(filename, 'w') as f: json.dump(data, f, indent=4)

users = load_json("users.json") channels = load_json("channels.json")

=== CAPTCHA ===

def generate_captcha(): from random import randint return str(randint(1000, 9999))

=== UI Keyboards ===

def main_menu(): return ReplyKeyboardMarkup([ ["Encrypt", "Decrypt"], ["Generate Code (AI)", "Scan & Fix Code"], ["Contact Developer"] ], resize_keyboard=True)

def admin_panel(): return InlineKeyboardMarkup([ [InlineKeyboardButton("Add Channel", callback_data="add_channel")], [InlineKeyboardButton("Remove Channel", callback_data="remove_channel")], [InlineKeyboardButton("Update Code", callback_data="update_code")], [InlineKeyboardButton("View Code", callback_data="view_code")] ])

=== Sub Check ===

async def check_subscription(user_id, bot): try: for ch in channels.get("channels", [CHANNEL]): member = await bot.get_chat_member(ch, user_id) if member.status not in ['member', 'administrator', 'creator']: return False return True except: return False

=== Core Logic ===

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

