#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOMAIT HUCK TOOL - Telegram Bot Server
السيرفر الكامل عبر Telegram - مجاني للأبد
"""

import os, json, secrets, datetime, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ══════════════════════════════════════════════════════════
#  إعداداتك الشخصية ← لا تغيّر هذه
# ══════════════════════════════════════════════════════════
BOT_TOKEN   = "8965335332:AAE9Jz0Tr2SPKxLVD66NbSIyB-ZUOTFrgX0"
ADMIN_ID    = 1033376307
APP_VERSION = "2.0.0"
DB_FILE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "komait_db.json")
API_PORT    = 5001

# ══════════════════════════════════════════════════════════
#  Telegram API Helper
# ══════════════════════════════════════════════════════════
import urllib.request, urllib.parse

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg(method: str, data: dict = None) -> dict:
    try:
        body = json.dumps(data or {}).encode()
        req  = urllib.request.Request(
            f"{TG}/{method}", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send(chat_id, text, markup=None):
    d = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if markup: d["reply_markup"] = markup
    return tg("sendMessage", d)

def edit(chat_id, msg_id, text, markup=None):
    d = {"chat_id": chat_id, "message_id": msg_id,
         "text": text, "parse_mode": "HTML"}
    if markup: d["reply_markup"] = markup
    return tg("editMessageText", d)

def answer_cb(cb_id, text=""):
    tg("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})

def btn(text, data):    return {"text": text, "callback_data": data}
def keyboard(rows):     return {"inline_keyboard": rows}

# ══════════════════════════════════════════════════════════
#  Database (JSON file)
# ══════════════════════════════════════════════════════════
def db_load() -> dict:
    default = {"users": {}, "activity": [], "games": [], "updates": [], "messages": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # تأكد أن كل الحقول موجودة
        for key in default:
            if key not in data:
                data[key] = default[key]
        return data
    except:
        return default

def db_save(db: dict):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True) if os.path.dirname(DB_FILE) else None
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def now_str() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def expire_after(days) -> str:
    if str(days) == "dev":
        return "2099-12-31 00:00:00"
    return (datetime.datetime.utcnow() +
            datetime.timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")

def days_left(expires: str) -> int:
    try:
        exp = datetime.datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        return max((exp - datetime.datetime.utcnow()).days, 0)
    except:
        return 0

def log_act(db, username, action, device="", game="", value="", status="", ip=""):
    db["activity"].insert(0, {
        "username": username, "action": action,
        "device": device, "game": game,
        "value": value, "status": status,
        "ip": ip, "ts": now_str()
    })
    db["activity"] = db["activity"][:500]

# ══════════════════════════════════════════════════════════
#  HTTP API Server (يُستدعى من البوت/التطبيق)
# ══════════════════════════════════════════════════════════
class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def _send(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")
        except:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/games/list":
            self._api_games()
        elif p == "/admin/api/games/list":
            self._api_games()
        elif p == "/api/version/latest":
            self._api_version()
        elif p == "/health":
            self._send({"ok": True, "server": "KOMAIT", "version": APP_VERSION})
        elif p == "/admin":
            self._admin_page()
        else:
            self._send({"ok": False}, 404)

    def do_POST(self):
        try:
         self._handle_post()
        except Exception as ex:
         try:
          self._send({"ok":False,"error":str(ex),"valid":False})
         except: pass

    def _handle_post(self):
        p    = self.path.split("?")[0]
        body = self._body()
        if   p == "/api/verify":         self._api_verify(body)
        elif p == "/api/log":            self._api_log(body)
        elif p == "/api/ping":           self._api_ping(body)
        elif p == "/api/games/list":     self._api_games()
        elif p == "/api/version/latest": self._api_version()
        elif p == "/api/message/send":            self._api_send_msg(body)
        elif p == "/api/message/get":             self._api_get_msgs(body)
        elif p == "/admin/api/message/send":      self._admin_send_msg(body)
        elif p == "/admin/api/message/list":      self._admin_get_msgs(body)
        elif p == "/admin/api/stats":    self._admin_stats()
        elif p == "/admin/api/users/list":   self._admin_users()
        elif p == "/admin/api/user/add":     self._admin_add_user(body)
        elif p == "/admin/api/user/renew":   self._admin_renew(body)
        elif p == "/admin/api/user/toggle":  self._admin_toggle(body)
        elif p == "/admin/api/user/delete":  self._admin_delete(body)
        elif p == "/admin/api/user/token":   self._admin_token(body)
        elif p == "/admin/api/games/add":    self._admin_add_game(body)
        elif p == "/admin/api/games/remove": self._admin_remove_game(body)
        elif p == "/admin/api/updates/push": self._admin_push_update(body)
        elif p == "/admin/api/updates/list": self._admin_updates()
        elif p == "/admin/api/activity/recent": self._admin_activity()
        elif p == "/admin/api/activity/user":   self._admin_user_activity(body)
        elif p == "/admin/api/online":       self._admin_online()
        else:
            self._send({"ok": False, "error": "Not found"}, 404)

    # ── BOT API ──────────────────────────────────────────
    def _api_verify(self, body):
        token = body.get("token","").strip()
        ip    = self.client_address[0]
        if not token:
            return self._send({"valid": False, "error": "No token"})
        db   = db_load()
        user = db["users"].get(token)
        if not user:
            return self._send({"valid": False, "error": "Invalid token"})
        if not user.get("active", True):
            return self._send({"valid": False, "error": "License suspended by admin"})
        plan = user.get("plan","30")
        if plan == "dev":
            user["last_seen"] = now_str()
            user["last_ip"]   = ip
            log_act(db, user["username"], "VERIFY_OK", ip=ip)
            db_save(db)
            return self._send({
                "valid": True, "username": user["username"],
                "expires": "2099-12-31 00:00:00", "days_left": 9999, "plan": "dev"
            })
        if not user.get("expires"):
            return self._send({"valid": False, "error": "Not activated yet"})
        dl = days_left(user["expires"])
        if dl <= 0:
            log_act(db, user["username"], "VERIFY_EXPIRED", ip=ip)
            db_save(db)
            return self._send({
                "valid": False, "error": "License expired",
                "expired_on": user["expires"]
            })
        user["last_seen"] = now_str()
        user["last_ip"]   = ip
        # تتبع الأجهزة - fingerprint بسيط من IP
        devices = user.setdefault("devices", [])
        # احفظ IP فريد كـ device identifier
        device_entry = next((d for d in devices if d.get("ip")==ip), None)
        if device_entry:
            device_entry["last_seen"] = now_str()
            device_entry["count"] = device_entry.get("count",0) + 1
        else:
            devices.append({"ip": ip, "first_seen": now_str(),
                            "last_seen": now_str(), "count": 1})
        user["device_count"] = len(devices)
        log_act(db, user["username"], "VERIFY_OK", ip=ip)
        db_save(db)
        # تحذير الأدمن إذا أكثر من 2 أجهزة
        if len(devices) > 2:
            _notify_admin(
                f"⚠️ <b>{user['username']}</b> using {len(devices)} devices!\n"
                f"IPs: {', '.join(d['ip'] for d in devices[-3:])}"
            )
        self._send({
            "valid": True, "username": user["username"],
            "expires": user["expires"], "days_left": dl, "plan": plan
        })

    def _api_log(self, body):
        token = body.get("token","")
        db    = db_load()
        user  = db["users"].get(token)
        if user:
            log_act(db, user["username"],
                    body.get("action",""), body.get("device",""),
                    body.get("game",""), body.get("value",""),
                    body.get("status",""))
            db_save(db)
        self._send({"ok": True})

    def _api_ping(self, body):
        token = body.get("token","")
        db    = db_load()
        user  = db["users"].get(token)
        if user:
            user["last_seen"] = now_str()
            db_save(db)
        self._send({"ok": True, "server_time": now_str()})

    def _api_games(self):
        db    = db_load()
        games = []
        for g in db.get("games",[]):
            games.append({
                "name":     g["name"],
                "package":  g["package"],
                "dev_key":  g["dev_key"],
                "id":       g.get("id",""),
                "IDFV":     g.get("IDFV",""),
                "level_events": [{
                    "display":  g.get("display", "Level"),
                    "template": g.get("template","level_{}_completed")
                }]
            })
        self._send({"games": games})

    def _api_version(self):
        db  = db_load()
        upd = db.get("updates",[])
        if upd:
            return self._send(upd[0])
        self._send({"version": APP_VERSION})

    def _api_send_msg(self, body):
        """المستخدم يرسل رسالة للأدمن"""
        token = body.get("token","")
        db    = db_load()
        user  = db["users"].get(token)
        if not user:
            return self._send({"ok":False,"error":"Invalid token"})
        msg = {
            "id":      len(db.get("messages",[])) + 1,
            "from":    user["username"],
            "to":      "admin",
            "text":    body.get("text",""),
            "ts":      now_str(),
            "read":    False,
            "type":    "user_to_admin"
        }
        db.setdefault("messages",[]).insert(0, msg)
        db_save(db)
        # إشعار الأدمن في تلغرام
        _notify_admin(f"💬 Message from <b>{user['username']}</b>:\n{body.get('text','')}")
        self._send({"ok":True})

    def _api_get_msgs(self, body):
        """المستخدم يجلب رسائله من الأدمن"""
        token = body.get("token","")
        db    = db_load()
        user  = db["users"].get(token)
        if not user:
            return self._send({"ok":False,"messages":[]})
        # رسائل موجهة لهذا المستخدم أو broadcast
        msgs = [m for m in db.get("messages",[])
                if m.get("to") == user["username"] or m.get("to") == "all"]
        self._send({"ok":True,"messages":msgs[:50]})

    def _admin_send_msg(self, body):
        """الأدمن يرسل رسالة لمستخدم أو للجميع"""
        db   = db_load()
        to   = body.get("to","all")  # اسم المستخدم أو "all"
        text = body.get("text","")
        msg  = {
            "id":   len(db.get("messages",[])) + 1,
            "from": "admin",
            "to":   to,
            "text": text,
            "ts":   now_str(),
            "read": False,
            "type": "admin_to_user"
        }
        db.setdefault("messages",[]).insert(0, msg)
        db_save(db)
        self._send({"ok":True})

    def _admin_get_msgs(self, body):
        """الأدمن يجلب كل الرسائل"""
        db   = db_load()
        msgs = db.get("messages",[])[:100]
        self._send({"ok":True,"messages":msgs})

    # ── ADMIN API (للتطبيق) ──────────────────────────────
    def _get_stats(self):
        db    = db_load()
        users = db["users"]
        total = len(users)
        active= sum(1 for u in users.values() if u.get("active",True))
        susp  = total - active
        cut   = (datetime.datetime.utcnow()-datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        online= sum(1 for u in users.values() if (u.get("last_seen") or "") >= cut)
        exp   = sum(1 for u in users.values()
                    if u.get("plan")!="dev" and u.get("active",True)
                    and u.get("expires") and days_left(u["expires"])<=0)
        inj   = sum(1 for a in db.get("activity",[])
                    if a.get("action")=="INJECT" and a.get("status")=="SUCCESS")
        return {"total":total,"active":active,"suspended":susp,
                "online":online,"expired":exp,"injections":inj}

    def _admin_stats(self):
        self._send(self._get_stats())

    def _admin_users(self):
        db    = db_load()
        now   = datetime.datetime.utcnow()
        users = []
        for token, u in db["users"].items():
            dl = 9999 if u.get("plan")=="dev" else days_left(u.get("expires",""))
            users.append({
                "id": token[:8], "token": token,
                "username": u["username"], "plan": u.get("plan","30"),
                "expires": u.get("expires",""), "active": u.get("active",True),
                "note": u.get("note",""), "last_seen": u.get("last_seen",""),
                "days_left": dl
            })
        users.sort(key=lambda x: x["username"])
        self._send({"users": users})

    def _admin_add_user(self, body):
        name = body.get("name","").strip()
        if not name:
            return self._send({"ok":False,"error":"Name required"})
        db = db_load()
        if any(u["username"]==name for u in db["users"].values()):
            return self._send({"ok":False,"error":f"User '{name}' already exists"})
        token   = secrets.token_hex(20)
        plan    = str(body.get("plan","30"))
        act     = body.get("activate", True)
        expires = expire_after(plan) if act else None
        db["users"][token] = {
            "username": name, "plan": plan,
            "expires": expires, "active": True,
            "note": body.get("note",""),
            "created": now_str(), "last_seen": None, "last_ip": None
        }
        db_save(db)
        # إشعار تلغرام
        _notify_admin(f"✅ New user <b>{name}</b> ({plan}d) created via app.")
        self._send({"ok":True,"token":token})

    def _admin_renew(self, body):
        token = body.get("id","")  # هنا id هو التوكن
        plan  = str(body.get("plan","30"))
        db    = db_load()
        # ابحث بالتوكن أو بالاسم
        user = db["users"].get(token)
        if not user:
            # ابحث بأول 8 حروف
            for tok, u in db["users"].items():
                if tok[:8] == token:
                    token = tok; user = u; break
        if not user:
            return self._send({"ok":False,"error":"User not found"})
        try:
            base = max(
                datetime.datetime.strptime(user.get("expires",""), "%Y-%m-%d %H:%M:%S"),
                datetime.datetime.utcnow()
            )
        except:
            base = datetime.datetime.utcnow()
        if plan == "dev":
            new_exp = "2099-12-31 00:00:00"
        else:
            new_exp = (base + datetime.timedelta(days=int(plan))).strftime("%Y-%m-%d %H:%M:%S")
        user["expires"] = new_exp
        user["plan"]    = plan
        db_save(db)
        _notify_admin(f"↺ <b>{user['username']}</b> renewed +{plan}d → {new_exp}")
        self._send({"ok":True,"new_expires":new_exp})

    def _admin_toggle(self, body):
        token  = body.get("id","")
        active = body.get("active", True)
        db     = db_load()
        user   = db["users"].get(token)
        if not user:
            for tok, u in db["users"].items():
                if tok[:8] == token:
                    user = u; break
        if not user:
            return self._send({"ok":False,"error":"Not found"})
        user["active"] = bool(active)
        db_save(db)
        act_str = "activated" if active else "suspended"
        _notify_admin(f"{'✅' if active else '⏸'} <b>{user['username']}</b> {act_str} via app.")
        self._send({"ok":True})

    def _admin_delete(self, body):
        token = body.get("id","")
        db    = db_load()
        found = False
        for tok in list(db["users"].keys()):
            if tok == token or tok[:8] == token:
                name = db["users"][tok]["username"]
                del db["users"][tok]
                found = True
                break
        if found:
            db_save(db)
            _notify_admin(f"🗑 User <b>{name}</b> deleted via app.")
        self._send({"ok": found})

    def _admin_token(self, body):
        uid = body.get("id","")
        db  = db_load()
        for tok, u in db["users"].items():
            if tok[:8] == uid or tok == uid:
                return self._send({"token": tok})
        self._send({"token": None})

    def _admin_add_game(self, body):
        name = body.get("name","").strip()
        if not name:
            return self._send({"ok":False,"error":"Name required"})
        db = db_load()
        if any(g["name"]==name for g in db.get("games",[])):
            return self._send({"ok":False,"error":"Game already exists"})
        db.setdefault("games",[]).append({
            "name": name, "package": body.get("package",""),
            "dev_key": body.get("dev_key",""),
            "template": body.get("template","level_{}_completed"),
            "added": now_str()
        })
        db_save(db)
        _notify_admin(f"🎮 Game <b>{name}</b> added to library.")
        self._send({"ok":True})

    def _admin_remove_game(self, body):
        name = body.get("name","")
        db   = db_load()
        before = len(db.get("games",[]))
        db["games"] = [g for g in db.get("games",[]) if g["name"]!=name]
        db_save(db)
        self._send({"ok": len(db["games"]) < before})

    def _admin_push_update(self, body):
        ver = body.get("version","")
        if not ver:
            return self._send({"ok":False,"error":"Version required"})
        db  = db_load()
        upd = {
            "version": ver, "type": body.get("type","required"),
            "notes": body.get("notes",""), "download_url": body.get("download_url",""),
            "pushed_at": now_str()
        }
        db["updates"].insert(0, upd)
        db_save(db)
        _notify_admin(f"📢 Update <b>v{ver}</b> pushed to all users ({upd['type']}).")
        self._send({"ok":True})

    def _admin_updates(self):
        db = db_load()
        self._send({"updates": db.get("updates",[])[:20]})

    def _admin_activity(self):
        db = db_load()
        self._send({"entries": db.get("activity",[])[:80]})

    def _admin_user_activity(self, body):
        username = body.get("username","")
        db       = db_load()
        entries  = [a for a in db.get("activity",[]) if a.get("username")==username][:100]
        self._send({"entries": entries})

    def _admin_online(self):
        db  = db_load()
        cut = (datetime.datetime.utcnow()-datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
        sessions = []
        for tok, u in db["users"].items():
            if u.get("last_seen","") >= cut:
                sessions.append({
                    "username": u["username"],
                    "client_ip": u.get("last_ip","--"),
                    "last_seen": u.get("last_seen","")
                })
        self._send({"sessions": sessions})

    # ── ADMIN WEB PAGE ───────────────────────────────────
    def _admin_page(self):
        html = b"<h1>KOMAIT Admin</h1><p>Use the desktop admin app.</p>"
        self.send_response(200)
        self.send_header("Content-Type","text/html")
        self.end_headers()
        self.wfile.write(html)


def _notify_admin(text: str):
    """إرسال إشعار للأدمن في تلغرام"""
    try:
        tg("sendMessage", {"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"})
    except:
        pass


def run_api():
    server = HTTPServer(("0.0.0.0", API_PORT), APIHandler)
    server.serve_forever()

# ══════════════════════════════════════════════════════════
#  TELEGRAM BOT COMMANDS
# ══════════════════════════════════════════════════════════

def is_admin(uid): return uid == ADMIN_ID

def handle_message(msg: dict):
    cid  = msg["chat"]["id"]
    text = msg.get("text","").strip()
    uid  = msg["from"]["id"]
    if not is_admin(uid):
        send(cid, "⛔ Access denied.")
        return

    if   text in ("/start","/help"):     cmd_help(cid)
    elif text == "/stats":               cmd_stats(cid)
    elif text == "/users":               cmd_users(cid)
    elif text == "/games":               cmd_games(cid)
    elif text == "/activity":            cmd_activity(cid)
    elif text == "/myid":                send(cid, f"Your ID: <code>{uid}</code>")
    elif text.startswith("/add "):       cmd_add(cid, text[5:])
    elif text.startswith("/renew "):     cmd_renew(cid, text[7:])
    elif text.startswith("/suspend "):   cmd_toggle(cid, text[9:], False)
    elif text.startswith("/activate "):  cmd_toggle(cid, text[10:], True)
    elif text.startswith("/delete "):    cmd_delete(cid, text[8:])
    elif text.startswith("/token "):     cmd_token(cid, text[7:])
    elif text.startswith("/logs "):      cmd_logs(cid, text[6:])
    elif text.startswith("/addgame "):   cmd_add_game(cid, text[9:])
    elif text.startswith("/removegame "): cmd_rm_game(cid, text[12:])
    elif text.startswith("/update "):    cmd_update(cid, text[8:])
    else: send(cid, "❓ Unknown. Send /help")


def handle_callback(cb: dict):
    cid    = cb["message"]["chat"]["id"]
    mid    = cb["message"]["message_id"]
    data   = cb.get("data","")
    uid    = cb["from"]["id"]
    answer_cb(cb["id"])
    if not is_admin(uid): return

    parts  = data.split(":")
    action = parts[0]
    token  = parts[1] if len(parts)>1 else ""

    if action == "umenu":
        _show_umenu(cid, mid, token)
    elif action == "suspend":
        db = db_load()
        if token in db["users"]:
            db["users"][token]["active"] = False
            db_save(db)
        _show_umenu(cid, mid, token, "⏸ Suspended!")
    elif action == "activate":
        db = db_load()
        if token in db["users"]:
            db["users"][token]["active"] = True
            db_save(db)
        _show_umenu(cid, mid, token, "✅ Activated!")
    elif action.startswith("renew_"):
        days = action.split("_")[1]
        db   = db_load()
        u    = db["users"].get(token)
        if u:
            try:
                base = max(
                    datetime.datetime.strptime(u.get("expires",""), "%Y-%m-%d %H:%M:%S"),
                    datetime.datetime.utcnow()
                )
            except:
                base = datetime.datetime.utcnow()
            u["expires"] = (base + datetime.timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")
            u["plan"]    = days
            db_save(db)
        _show_umenu(cid, mid, token, f"✅ +{days} days added!")
    elif action == "back":
        cmd_users_inline(cid, mid)


def _show_umenu(cid, mid, token, note=""):
    db   = db_load()
    u    = db["users"].get(token)
    if not u:
        edit(cid, mid, "User not found.")
        return
    plan = u.get("plan","30")
    dl   = "∞" if plan=="dev" else str(days_left(u.get("expires","")))
    st   = "✅ ACTIVE" if u.get("active",True) else "⏸ SUSPENDED"
    txt  = (
        f"👤 <b>{u['username']}</b>  {note}\n\n"
        f"Status  : {st}\n"
        f"Plan    : {plan}\n"
        f"Expires : {u.get('expires','--')}\n"
        f"Days    : {dl}\n"
        f"Last    : {u.get('last_seen','never')}\n"
        f"IP      : {u.get('last_ip','--')}\n"
        f"Note    : {u.get('note','--')}"
    )
    rows = []
    if u.get("active",True):
        rows.append([btn("⏸ Suspend", f"suspend:{token}")])
    else:
        rows.append([btn("▶️ Activate", f"activate:{token}")])
    rows.append([
        btn("+15d", f"renew_15:{token}"),
        btn("+30d", f"renew_30:{token}"),
        btn("+90d", f"renew_90:{token}"),
        btn("+1yr", f"renew_365:{token}"),
    ])
    rows.append([btn("◀️ Back", "back:")])
    edit(cid, mid, txt, keyboard(rows))


def cmd_help(cid):
    send(cid, """
<b>🔑 KOMAIT HUCK TOOL — Admin</b>

<b>👥 Users:</b>
/add username days [note]
/add username dev [note]
/users
/token username
/logs username
/suspend username
/activate username
/renew username days
/delete username

<b>🎮 Games:</b>
/addgame Name|Package|DevKey|Template
/removegame Name
/games

<b>📊 Info:</b>
/stats
/activity

<b>🔄 Updates:</b>
/update version|type|notes|url
  type: required / optional

<b>ℹ️</b>
/myid  — your Telegram ID
""")


def cmd_stats(cid):
    db    = db_load()
    users = db["users"]
    total = len(users)
    active= sum(1 for u in users.values() if u.get("active",True))
    cut   = (datetime.datetime.utcnow()-datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    online= sum(1 for u in users.values() if (u.get("last_seen") or "") >= cut)
    inj   = sum(1 for a in db.get("activity",[])
                if a.get("action")=="INJECT" and a.get("status")=="SUCCESS")
    send(cid, f"""
📊 <b>STATS</b>

👥 Users  : <b>{total}</b> total / <b>{active}</b> active
🟢 Online  : <b>{online}</b> (last 10 min)
💉 Inject  : <b>{inj}</b> success
🎮 Games   : <b>{len(db.get('games',[]))}</b>
🕒 Time    : <code>{now_str()} UTC</code>
""")


def cmd_users(cid):
    db    = db_load()
    users = db["users"]
    if not users:
        send(cid, "No users yet.\n/add username 30 note")
        return
    txt = "👥 <b>USERS</b> — tap to manage:\n"
    rows = []
    for tok, u in list(users.items()):
        plan = u.get("plan","30")
        dl   = "∞" if plan=="dev" else f"{days_left(u.get('expires',''))}d"
        ico  = "✅" if u.get("active",True) else "⏸"
        rows.append([btn(f"{ico} {u['username']} · {dl}", f"umenu:{tok}")])
    send(cid, txt, keyboard(rows[:15]))


def cmd_users_inline(cid, mid):
    db    = db_load()
    users = db["users"]
    txt   = "👥 <b>USERS</b> — tap to manage:"
    rows  = []
    for tok, u in list(users.items()):
        plan = u.get("plan","30")
        dl   = "∞" if plan=="dev" else f"{days_left(u.get('expires',''))}d"
        ico  = "✅" if u.get("active",True) else "⏸"
        rows.append([btn(f"{ico} {u['username']} · {dl}", f"umenu:{tok}")])
    edit(cid, mid, txt, keyboard(rows[:15]))


def cmd_add(cid, args):
    parts    = args.split(" ", 2)
    username = parts[0].strip()
    plan     = parts[1].strip() if len(parts)>1 else "30"
    note     = parts[2].strip() if len(parts)>2 else ""
    if not username:
        send(cid, "Usage: /add username [days|dev] [note]")
        return
    db = db_load()
    if any(u["username"]==username for u in db["users"].values()):
        send(cid, f"❌ '{username}' already exists!")
        return
    token   = secrets.token_hex(20)
    expires = expire_after(plan)
    db["users"][token] = {
        "username": username, "plan": plan, "expires": expires,
        "active": True, "note": note, "created": now_str(),
        "last_seen": None, "last_ip": None
    }
    db_save(db)
    send(cid, f"""
✅ <b>User Created!</b>

👤 <b>{username}</b>
📅 Plan    : {plan} {'days' if plan!='dev' else '(unlimited)'}
📆 Expires : <code>{expires}</code>
📝 Note    : {note or '--'}

🔑 Token (send to user):
<code>{token}</code>

<i>User pastes this token on first launch.</i>
""")


def cmd_renew(cid, args):
    parts    = args.split()
    username = parts[0] if parts else ""
    plan     = parts[1] if len(parts)>1 else "30"
    db = db_load()
    for tok, u in db["users"].items():
        if u["username"] == username:
            try:
                base = max(
                    datetime.datetime.strptime(u.get("expires",""), "%Y-%m-%d %H:%M:%S"),
                    datetime.datetime.utcnow()
                )
            except:
                base = datetime.datetime.utcnow()
            new_exp = "2099-12-31 00:00:00" if plan=="dev" else \
                      (base + datetime.timedelta(days=int(plan))).strftime("%Y-%m-%d %H:%M:%S")
            u["expires"] = new_exp
            u["plan"]    = plan
            db_save(db)
            send(cid, f"✅ <b>{username}</b> renewed +{plan} days!\nNew expiry: <code>{new_exp}</code>")
            return
    send(cid, f"❌ '{username}' not found.")


def cmd_toggle(cid, username, active):
    db = db_load()
    for u in db["users"].values():
        if u["username"] == username:
            u["active"] = active
            db_save(db)
            s = "✅ Activated" if active else "⏸ Suspended"
            send(cid, f"{s}: <b>{username}</b>")
            return
    send(cid, f"❌ '{username}' not found.")


def cmd_delete(cid, username):
    db = db_load()
    for tok in list(db["users"].keys()):
        if db["users"][tok]["username"] == username:
            del db["users"][tok]
            db_save(db)
            send(cid, f"🗑 <b>{username}</b> deleted.")
            return
    send(cid, f"❌ '{username}' not found.")


def cmd_token(cid, username):
    db = db_load()
    for tok, u in db["users"].items():
        if u["username"] == username:
            send(cid, f"🔑 Token for <b>{username}</b>:\n\n<code>{tok}</code>")
            return
    send(cid, f"❌ '{username}' not found.")


def cmd_logs(cid, username):
    db   = db_load()
    logs = [a for a in db.get("activity",[]) if a.get("username")==username][:15]
    if not logs:
        send(cid, f"No logs for <b>{username}</b>")
        return
    txt = f"📋 <b>Logs: {username}</b>\n\n"
    for a in logs:
        s = "✅" if "SUCCESS" in a.get("status","") else ("❌" if "FAIL" in a.get("status","") else "ℹ️")
        txt += f"{s} <code>{a['ts'][-8:]}</code> {a['action']}"
        if a.get("game"):  txt += f" → {a['game']}"
        if a.get("value"): txt += f" = {a['value']}"
        txt += "\n"
    send(cid, txt)


def cmd_activity(cid):
    db   = db_load()
    logs = db.get("activity",[])[:20]
    if not logs:
        send(cid, "No activity yet.")
        return
    txt = "📊 <b>RECENT ACTIVITY</b>\n\n"
    for a in logs:
        s = "✅" if "SUCCESS" in a.get("status","") else ("❌" if "FAIL" in a.get("status","") else "ℹ️")
        txt += f"{s} <b>{a['username']}</b> · {a['ts'][-8:]} · {a['action']}"
        if a.get("game"): txt += f" · {a['game']}"
        txt += "\n"
    send(cid, txt)


def cmd_games(cid):
    db = db_load()
    gs = db.get("games",[])
    if not gs:
        send(cid, "No games.\n/addgame Name|Package|DevKey|Template")
        return
    txt = "🎮 <b>GAMES LIBRARY</b>\n\n"
    for i, g in enumerate(gs, 1):
        txt += f"{i}. <b>{g['name']}</b>\n   <code>{g['package']}</code>\n"
    send(cid, txt)


def cmd_add_game(cid, args):
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        send(cid, "Usage:\n/addgame Name|PackageID|DevKey|event_template\n\nExample:\n/addgame Coin Master|id406889139|H3KjoCRVTiVgA5|level_{}_completed")
        return
    db = db_load()
    if any(g["name"]==parts[0] for g in db.get("games",[])):
        send(cid, f"❌ '{parts[0]}' already exists!")
        return
    db.setdefault("games",[]).append({
        "name": parts[0], "package": parts[1], "dev_key": parts[2],
        "template": parts[3] if len(parts)>3 else "level_{}_completed",
        "added": now_str()
    })
    db_save(db)
    send(cid, f"✅ Game added!\n\n🎮 <b>{parts[0]}</b>\n📦 {parts[1]}")


def cmd_rm_game(cid, name):
    db     = db_load()
    before = len(db.get("games",[]))
    db["games"] = [g for g in db.get("games",[]) if g["name"]!=name]
    if len(db["games"]) < before:
        db_save(db)
        send(cid, f"🗑 '{name}' removed!")
    else:
        send(cid, f"❌ '{name}' not found.")


def cmd_update(cid, args):
    parts = [p.strip() for p in args.split("|")]
    if not parts[0]:
        send(cid, "Usage:\n/update version|type|notes|download_url\n\nExample:\n/update 2.1.0|required|Bug fixes|https://...")
        return
    db = db_load()
    upd = {
        "version": parts[0],
        "type": parts[1] if len(parts)>1 else "required",
        "notes": parts[2] if len(parts)>2 else "",
        "download_url": parts[3] if len(parts)>3 else "",
        "pushed_at": now_str()
    }
    db["updates"].insert(0, upd)
    db_save(db)
    send(cid, f"📢 Update pushed!\n\nVersion: <b>{upd['version']}</b>\nType: {upd['type']}\nNotes: {upd['notes']}\n\n<i>All users see this on next launch.</i>")


# ══════════════════════════════════════════════════════════
#  POLLING
# ══════════════════════════════════════════════════════════
def poll():
    print(f"  [OK] Telegram bot started (Admin ID: {ADMIN_ID})")
    # حذف أي webhooks قديمة
    tg("deleteWebhook")
    # إشعار الأدمن
    send(ADMIN_ID, f"🟢 <b>KOMAIT Server is ONLINE!</b>\n\nVersion: {APP_VERSION}\nSend /help to manage users.")
    offset = 0
    while True:
        try:
            r = tg("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message","callback_query"]})
            if not r.get("ok"):
                time.sleep(3)
                continue
            for upd in r.get("result",[]):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    handle_message(upd["message"])
                elif "callback_query" in upd:
                    handle_callback(upd["callback_query"])
        except KeyboardInterrupt:
            print("\n  [*] Stopped.")
            send(ADMIN_ID, "🔴 Server stopped.")
            break
        except Exception as e:
            print(f"  [!] Error: {e}")
            time.sleep(5)


# ══════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║   KOMAIT HUCK TOOL - Telegram Server  ║")
    print("  ║   WhatsApp: 0992111585                ║")
    print("  ╚═══════════════════════════════════════╝")
    print(f"  Bot Token : {BOT_TOKEN[:25]}...")
    print(f"  Admin ID  : {ADMIN_ID}")
    print(f"  API Port  : {API_PORT}")
    print()

    # API server في الخلفية
    t = threading.Thread(target=run_api, daemon=True)
    t.start()
    print(f"  [OK] API Server running on port {API_PORT}")

    # Telegram polling
    poll()
