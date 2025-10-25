# -*- coding: utf-8 -*-
"""
A SEED — Flask server (Ollama backend) - FINAL VERSION V2
- User authentication with display name and password confirmation
- Chat endpoint /api/chat
- Session management per user
- Full Admin dashboard with stats and restart functionality
"""
import os
import sys
import json
import time
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

import psutil
import requests
from flask import (
    Flask, request, jsonify, session, g, redirect, make_response, render_template
)
from werkzeug.security import generate_password_hash, check_password_hash

# Safely initialize PyNVML for GPU monitoring
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

# =========================
# ====== Config & Paths ===
# =========================
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
SESS_DIR   = DATA_DIR / "sessions"
STATIC_DIR = BASE_DIR / "static"
TRAIN_DIR  = BASE_DIR / "training"
USERS_FILE = DATA_DIR / "users.json"

for d in (DATA_DIR, SESS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Ollama Config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL_NAME  = os.getenv("MODEL_NAME", "gpt-oss:120b-cloud")
NUM_CTX     = int(os.getenv("NUM_CTX", "4096"))
GEN_TEMP    = float(os.getenv("GEN_TEMP", "0.7"))
TOP_P       = float(os.getenv("TOP_P", "0.9"))

# Admin & Secret Key
ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY     = os.getenv("SECRET_KEY", "a-seed-secret-key-dev")

# Flask App Initialization
app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder='templates')
app.secret_key = SECRET_KEY
app.config.update(SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=False)

# Runtime Variables
START_TS = time.time()
REQUEST_LOGS: List[Dict[str, Any]] = []
MAX_REQ_LOGS = 100

# =========================
# ======= User Auth Utils ======
# =========================
def read_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def write_users(users: Dict[str, Any]):
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# =========================
# ======= General Utils ========
# =========================
def now_ts() -> int:
    return int(time.time())

def safe_json(s: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

def ensure_sid(sid: str) -> str:
    return sid or str(uuid.uuid4())

def get_user_session_dir() -> Path:
    user_id = session.get('user_id')
    if not user_id:
        return None
    safe_user_id = re.sub(r'[^\w-]', '', user_id)
    user_dir = SESS_DIR / safe_user_id
    user_dir.mkdir(exist_ok=True)
    return user_dir

def session_path(sid: str) -> Path:
    user_dir = get_user_session_dir()
    safe_sid = re.sub(r'[^\w-]', '', sid)
    return user_dir / f"{safe_sid}.json" if user_dir else None

def write_json(path: Path, obj: Any):
    if not path: return
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)

def read_json(path: Path) -> Any:
    if not path or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# =========================
# ====== Ollama & AI Backend ======
# =========================
def ollama_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    url     = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model":    MODEL_NAME,
        "messages": messages,
        "stream":   False,
        "options":  {"num_ctx": NUM_CTX, "temperature": GEN_TEMP, "top_p": TOP_P},
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data    = r.json()
    content = data.get("message", {}).get("content", "")
    return {"raw": data, "text": content}

def get_system_prompt() -> str:
    prompt_file = TRAIN_DIR / "a_seed_prompt.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "You are a helpful and empathetic assistant named A SEED."

# ===========================================
# =========== Auth Pages & API (UPDATED) ====
# ===========================================
@app.route("/")
def root():
    if 'user_id' in session:
        return redirect('/chat')
    return redirect('/login')

@app.route("/chat")
def chat_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    users = read_users()
    display_name = users.get(user_id, {}).get('display_name', user_id)
    
    return render_template('index.html', display_name=display_name)

@app.route("/login")
def login_page():
    return render_template('login.html')

@app.post("/api/register")
def api_register():
    data = request.get_json()
    username = data.get('username', '').strip()
    display_name = data.get('displayName', '').strip()
    password = data.get('password', '').strip()

    if not all([username, display_name, password]):
        return jsonify({"ok": False, "error": "All fields are required"}), 400

    users = read_users()
    if username in users:
        return jsonify({"ok": False, "error": "Username already exists"}), 409

    users[username] = { 
        "hash": generate_password_hash(password),
        "display_name": display_name,
        "created_at": now_ts() 
    }
    write_users(users)
    return jsonify({"ok": True, "message": "User created successfully"})

@app.post("/api/login")
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    users = read_users()

    user_data = users.get(username)
    if user_data and check_password_hash(user_data['hash'], password):
        session['user_id'] = username
        session['display_name'] = user_data.get('display_name', username)
        return jsonify({"ok": True, "displayName": session['display_name']})

    return jsonify({"ok": False, "error": "Invalid credentials"}), 401

@app.post("/api/logout")
def api_logout():
    session.pop('user_id', None)
    session.pop('display_name', None)
    return jsonify({"ok": True})

@app.get("/api/session-check")
def api_session_check():
    return jsonify({"logged_in": 'user_id' in session})

# ===========================================
# =============== Chat API ==================
# ===========================================
@app.post("/api/chat")
def api_chat():
    if 'user_id' not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    user_msg = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_msg:
        return jsonify({"error": "empty-message"}), 400

    sys_prompt = get_system_prompt()
    
    msgs = [{"role": "system", "content": sys_prompt}]
    for turn in history:
        if turn.get('role') in ['user', 'assistant']:
            msgs.append({"role": turn['role'], "content": turn['text']})
    msgs.append({"role": "user", "content": user_msg})

    try:
        out = ollama_chat(msgs)
        text = out.get("text") or ""
    except Exception as e:
        return jsonify({"error": "backend-failed", "hint": str(e)}), 500

    obj = safe_json(text)
    reply = (obj.get("reply") or text.strip() or "I'm not sure how to respond to that. Could you rephrase?").strip()
    emo = (obj.get("emotion") or "neutral").lower().strip()
    
    return jsonify({"emotion": emo, "reply": reply})

# ===========================================
# ========= Sessions Save/Load etc ==========
# ===========================================
@app.post("/api/save")
def api_save():
    if 'user_id' not in session: return jsonify({"error": "unauthorized"}), 401
    
    data = request.get_json()
    sid = ensure_sid(data.get("sid"))
    chat = data.get("chat") or []
    path = session_path(sid)
    
    if path:
        first_user_message = next((item['text'] for item in chat if item['role'] == 'user'), "New Chat")
        title = first_user_message[:60]
        
        write_json(path, {"sid": sid, "title": title, "chat": chat, "updated": now_ts()})
        return jsonify({"ok": True, "sid": sid, "title": title})
    return jsonify({"ok": False, "error": "could_not_get_session_path"}), 500

@app.get("/api/sessions")
def api_sessions():
    if 'user_id' not in session: return jsonify({"error": "unauthorized"}), 401
    
    user_dir = get_user_session_dir()
    if not user_dir: return jsonify([])

    res = []
    for p in user_dir.glob("*.json"):
        try:
            obj = read_json(p) or {}
            res.append({
                "sid": obj.get("sid") or p.stem,
                "title": obj.get("title") or p.stem,
                "count": len(obj.get("chat") or []),
                "updated": obj.get("updated") or int(p.stat().st_mtime),
            })
        except Exception: pass
    
    res.sort(key=lambda x: x["updated"], reverse=True)
    return jsonify(res)

@app.get("/api/load")
def api_load():
    if 'user_id' not in session: return jsonify({"error": "unauthorized"}), 401
    
    sid = request.args.get("sid") or ""
    path = session_path(sid)
    if not path:
        return jsonify({"error": "invalid_session_id"}), 400
    obj = read_json(path)
    if not obj:
        return jsonify({"error": "not-found"}), 404
    return jsonify(obj)

# ===========================================
# =============== Admin Section =============
# ===========================================
def nvidia_query() -> List[Dict[str, Any]]:
    if not NVML_AVAILABLE:
        return None
    try:
        gpus = []
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpus.append({
                "name": name.decode('utf-8') if isinstance(name, bytes) else name,
                "memory_total_mb": mem_info.total // (1024**2),
                "memory_used_mb":  mem_info.used // (1024**2),
                "util_percent":    util.gpu,
            })
        return gpus
    except Exception:
        return None

def safe_ollama_get(path, timeout=2.0):
    try:
        r = requests.get(OLLAMA_HOST + path, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@app.route("/admin")
def admin_page():
    if session.get("admin"):
        return redirect("/admin/dashboard")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")
    return render_template("admin.html")

@app.post("/api/admin/login")
def admin_login():
    data = request.get_json()
    if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401

@app.post("/api/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.get("/api/admin/status")
def admin_status():
    return jsonify({"logged_in": bool(session.get("admin"))})

@app.post("/api/admin/restart")
def api_restart():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401
    
    print("--- SERVER RESTART INITIATED BY ADMIN ---", flush=True)
    
    try:
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    
    return jsonify({"ok": True}) 

@app.get("/api/stats")
def api_stats():
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401

    now = time.time()
    mem = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    
    tags = safe_ollama_get("/api/tags")
    
    info = {
        "ts": int(now),
        "uptime_sec": int(now - START_TS),
        "python_version": sys.version.split(" ")[0],
        "cpu": {"percent": psutil.cpu_percent(interval=0.1)},
        "memory": {"total": mem.total, "used": mem.used, "percent": mem.percent},
        "process": {"pid": proc.pid, "rss_bytes": proc.memory_info().rss},
        "ollama": {
            "ok": bool(tags),
            "host": OLLAMA_HOST,
            "model_name": MODEL_NAME,
            "models_count": len(tags.get("models", [])) if tags else "N/A",
        },
        "gpus": nvidia_query()
    }
    return jsonify(info)

# =========================
# ========= Main ==========
# =========================
if __name__ == "__main__":
    # Host '0.0.0.0' allows access from other devices on the same network (e.g., your phone)
    host  = "0.0.0.0" 
    port  = 8000
    
    # This function will print your local IP address to make it easy to find
    def print_network_info():
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"   - On your phone, access via: http://{local_ip}:{port}", flush=True)
        except Exception:
            print("   - Could not determine local IP. Find it manually via 'ipconfig' command.", flush=True)

    print(f"🌱 A SEED server starting...", flush=True)
    print(f"   - On this computer, you can use: http://127.0.0.1:{port}", flush=True)
    print_network_info()
    
    # Use Waitress, a production-ready server that works well on Windows
    from waitress import serve
    print(f"   - Server is live. Press Ctrl+C in this window to stop.", flush=True)
    serve(app, host=host, port=port)