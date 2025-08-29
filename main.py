import os, json, time, asyncio, logging, difflib, math
from typing import Dict, Any, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

BOT_TOKEN = "8263269951:AAEZ52DKTruGI6ujfHjq4gh9ZK0JDWinBks"
ADMIN_ID = 7912879029
MANDATORY_CHANNELS = ["@imprimex"]
DB_FILES = "files_db.json"
DB_USERS = "users_db.json"
DB_STATS = "stats_db.json"
WAITING_FILE, WAITING_KEYWORD, CONFIRMATION = range(3)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("primex")

class KV:
    def __init__(self, path): self.path=path; self.data=self._load()
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path,"r",encoding="utf-8") as f: return json.load(f)
            except: return {}
        return {}
    def save(self): 
        tmp=self.path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f: json.dump(self.data,f,ensure_ascii=False,indent=2)
        os.replace(tmp,self.path)
    def get(self,k,default=None): return self.data.get(k,default)
    def set(self,k,v): self.data[k]=v; self.save()
    def delete(self,k): 
        if k in self.data: del self.data[k]; self.save()
    def keys(self): return list(self.data.keys())
    def items(self): return list(self.data.items())
    def clear(self): self.data={}; self.save()

files_kv = KV(DB_FILES)
users_kv = KV(DB_USERS)
stats_kv = KV(DB_STATS)

class RL:
    def __init__(self, per_user_rate: float, burst: int): self.rate=per_user_rate; self.burst=burst; self.bucket: Dict[int,Tuple[float,float]]={}
    def allow(self, uid: int) -> bool:
        now=time.monotonic()
        tokens, last=self.bucket.get(uid,(self.burst, now))
        tokens=min(self.burst, tokens + (now-last)*self.rate)
        if tokens>=1:
            tokens-=1; self.bucket[uid]=(tokens, now); return True
        self.bucket[uid]=(tokens, now); return False
rl_text = RL(0.5, 3)

class Channels:
    def __init__(self, req: List[str]): self.req=req
    async def ok(self, bot, uid:int)->bool:
        for ch in self.req:
            try:
                m=await bot.get_chat_member(ch, uid)
                if m.status in ("left","kicked"): return False
            except: return False
        return True
    def kb(self)->InlineKeyboardMarkup:
        rows=[[InlineKeyboardButton(ch, url=f"https://t.me/{ch[1:]}")] for ch in self.req]
        rows.append([InlineKeyboardButton("تحقق", callback_data="chk")])
        return InlineKeyboardMarkup(rows)

channels = Channels(MANDATORY_CHANNELS)

class Pager:
    def __init__(self, page_size:int=10): self.n=page_size
    def slice(self, items: List[str], page:int)->Tuple[List[str],int]:
        total=max(1, math.ceil(len(items)/self.n)) if items else 1
        page=max(1,min(page,total))
        start=(page-1)*self.n; return items[start:start+self.n], total
    def nav(self, page:int, total:int, prefix:str)->InlineKeyboardMarkup:
        btns=[]
        if page>1: btns.append(InlineKeyboardButton("«", callback_data=f"{prefix}|{page-1}"))
        btns.append(InlineKeyboardButton(f"{page}/{total}", callback_data="noop"))
        if page<total: btns.append(InlineKeyboardButton("»", callback_data=f"{prefix}|{page+1}"))
        return InlineKeyboardMarkup([btns]) if btns else InlineKeyboardMarkup([[InlineKeyboardButton("1/1",callback_data="noop")]])

pager = Pager(8)

class Files:
    def add(self, key:str, file_id:str): files_kv.set(key, file_id)
    def get(self, key:str)->str|None: return files_kv.get(key)
    def delete(self, key:str): files_kv.delete(key)
    def list(self)->List[str]: return sorted(files_kv.keys())
    def search(self, query:str)->Tuple[str|None,List[str]]:
        exact=files_kv.get(query)
        if exact: return exact,[query]
        keys=self.list()
        close=difflib.get_close_matches(query, keys, n=5, cutoff=0.6)
        return None, close

files = Files()

class Users:
    def seen(self, uid:int, name:str):
        u=users_kv.get(str(uid),{"id":uid,"name":name,"joined":int(time.time()),"hits":0})
        u["name"]=name; users_kv.set(str(uid), u)
    def hit(self, uid:int): 
        u=users_kv.get(str(uid)); 
        if u: u["hits"]=u.get("hits",0)+1; users_kv.set(str(uid),u)
    def count(self)->int: return len(users_kv.data)

users = Users()

class Stats:
    def inc(self, k:str, by:int=1):
        v=stats_kv.get(k,0)+by; stats_kv.set(k,v)
    def get(self,k:str,default=0): return stats_kv.get(k,default)
    def summary(self)->str:
        return "\n".join([
            f"users: {users.count()}",
            f"files: {len(files_kv.data)}",
            f"queries: {self.get('queries',0)}",
            f"delivered: {self.get('delivered',0)}",
            f"denied: {self.get('denied',0)}"
        ])

stats = Stats()

class UI:
    @staticmethod
    def home_kb()->InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="help")]])
    @staticmethod
    def admin_kb()->InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Add File", callback_data="add_file"), InlineKeyboardButton("List Files", callback_data="list|1")],
            [InlineKeyboardButton("Stats", callback_data="stats"), InlineKeyboardButton("Channels", callback_data="chs")]
        ])
    @staticmethod
    def confirm_kb()->InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("yes", callback_data="cfm|yes"), InlineKeyboardButton("no", callback_data="cfm|no")]])

class Flow:
    def __init__(self): self.buf: Dict[int,Dict[str,Any]]={}
    def set(self, uid:int, k:str, v:Any):
        self.buf.setdefault(uid,{})[k]=v
    def get(self, uid:int, k:str): return self.buf.get(uid,{}).get(k)
    def clear(self, uid:int): self.buf.pop(uid, None)

flow = Flow()

class Bot:
    def __init__(self, app: Application):
        self.app=app
        self.register()
    async def start(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        users.seen(u.effective_user.id, u.effective_user.full_name or "")
        await u.message.reply_text(f"Welcome {u.effective_user.first_name}", reply_markup=UI.home_kb())
    async def help(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        txt = "\n".join([
            "اكتب كلمة مفتاحية للحصول على الملف المرتبط بها.",
            "/add لإضافة ملف (مسؤول)",
            "/del <keyword> حذف ملف (مسؤول)",
            "/list عرض الملفات (مسؤول)",
            "/stats إحصائيات (مسؤول)"
        ])
        await u.message.reply_text(txt)
    async def admin(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if u.effective_user.id!=ADMIN_ID: return await u.message.reply_text("Access denied")
        await u.message.reply_text("Admin Panel", reply_markup=UI.admin_kb())
    async def add_entry(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if u.effective_user.id!=ADMIN_ID: return await u.message.reply_text("Access denied")
        await u.message.reply_text("Send file")
        return WAITING_FILE
    async def recv_file(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if not u.message.document: return await u.message.reply_text("Send valid file")
        flow.set(u.effective_user.id,"file_id", u.message.document.file_id)
        await u.message.reply_text("Send keyword")
        return WAITING_KEYWORD
    async def recv_keyword(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        kw=u.message.text.strip().lower()
        flow.set(u.effective_user.id,"keyword", kw)
        await u.message.reply_text(f"Confirm '{kw}'", reply_markup=UI.confirm_kb())
        return CONFIRMATION
    async def confirm_add(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        return ConversationHandler.END
    async def cancel(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        flow.clear(u.effective_user.id)
        await u.message.reply_text("Cancelled")
        return ConversationHandler.END
    async def on_text(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if not u.message or not u.message.text: return
        if not rl_text.allow(u.effective_user.id): return await u.message.reply_text("Slow down")
        if not await channels.ok(c.bot, u.effective_user.id):
            stats.inc("denied",1)
            return await u.message.reply_text("انضم للقنوات المطلوبة ثم اضغط تحقق", reply_markup=channels.kb())
        q=u.message.text.strip().lower()
        users.seen(u.effective_user.id, u.effective_user.full_name or "")
        stats.inc("queries",1)
        exact=files.get(q)
        if exact:
            users.hit(u.effective_user.id)
            stats.inc("delivered",1)
            return await u.message.reply_document(exact)
        _, close = files.search(q)
        if close:
            kb=InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=f"get|{k}") for k in close]])
            return await u.message.reply_text("Did you mean:", reply_markup=kb)
        await u.message.reply_text("Not found")
    async def on_cb(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        q=u.callback_query; await q.answer(); data=q.data or ""
        if data=="help": 
            return await q.edit_message_text("اكتب الكلمة المفتاحية أو استعمل /add و /admin للمزيد")
        if data=="chk":
            ok=await channels.ok(c.bot, q.from_user.id)
            return await q.edit_message_text("تم التحقق" if ok else "ما زلت غير مشترك")
        if data.startswith("get|"):
            key=data.split("|",1)[1]
            f=files.get(key)
            if f: 
                users.hit(q.from_user.id); stats.inc("delivered",1)
                try: await q.message.reply_document(f)
                except: pass
            else:
                await q.edit_message_text("Not found")
        if data=="stats":
            if q.from_user.id!=ADMIN_ID: return await q.answer("Denied", show_alert=True)
            return await q.edit_message_text(stats.summary())
        if data=="chs":
            if q.from_user.id!=ADMIN_ID: return await q.answer("Denied", show_alert=True)
            return await q.edit_message_text("Channels:\n"+"\n".join(MANDATORY_CHANNELS))
        if data=="add_file":
            if q.from_user.id!=ADMIN_ID: return await q.answer("Denied", show_alert=True)
            await q.message.reply_text("Use /add")
        if data.startswith("list|"):
            if q.from_user.id!=ADMIN_ID: return await q.answer("Denied", show_alert=True)
            page=int(data.split("|",1)[1])
            lst=files.list()
            chunk,total=pager.slice(lst,page)
            text="Files:\n"+"\n".join(chunk) if chunk else "No files"
            return await q.edit_message_text(text, reply_markup=pager.nav(page,total,"list"))
        if data.startswith("cfm|"):
            ans=data.split("|",1)[1]
            if q.from_user.id!=ADMIN_ID: return await q.answer("Denied", show_alert=True)
            if ans=="yes":
                fid=flow.get(q.from_user.id,"file_id"); kw=flow.get(q.from_user.id,"keyword")
                if fid and kw: files.add(kw,fid); flow.clear(q.from_user.id); return await q.edit_message_text("Saved")
                return await q.edit_message_text("Invalid")
            else:
                flow.clear(q.from_user.id); return await q.edit_message_text("Cancelled")
    async def cmd_list(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if u.effective_user.id!=ADMIN_ID: return await u.message.reply_text("Access denied")
        lst=files.list()
        chunk,total=pager.slice(lst,1)
        await u.message.reply_text("Files:\n"+"\n".join(chunk) if chunk else "No files", reply_markup=pager.nav(1,total,"list"))
    async def cmd_del(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if u.effective_user.id!=ADMIN_ID: return await u.message.reply_text("Access denied")
        args=u.message.text.split(maxsplit=1)
        if len(args)<2: return await u.message.reply_text("Usage: /del <keyword>")
        files.delete(args[1].strip().lower())
        await u.message.reply_text("Deleted")
    async def cmd_stats(self, u:Update, c:ContextTypes.DEFAULT_TYPE):
        if u.effective_user.id!=ADMIN_ID: return await u.message.reply_text("Access denied")
        await u.message.reply_text(stats.summary())
    def register(self):
        conv=ConversationHandler(
            entry_points=[CommandHandler("add", self.add_entry)],
            states={
                WAITING_FILE:[MessageHandler(filters.Document.ALL, self.recv_file)],
                WAITING_KEYWORD:[MessageHandler(filters.TEXT & ~filters.COMMAND, self.recv_keyword)],
                CONFIRMATION:[CallbackQueryHandler(self.on_cb, pattern="^cfm\\|.*")]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("admin", self.admin))
        self.app.add_handler(CommandHandler("list", self.cmd_list))
        self.app.add_handler(CommandHandler("del", self.cmd_del))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(conv)
        self.app.add_handler(CallbackQueryHandler(self.on_cb))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    Bot(app)
    app.run_polling()

if __name__=="__main__":
    main()        f"Welcome {user.first_name}!\n\nThis bot allows you to search files using keywords.",
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
