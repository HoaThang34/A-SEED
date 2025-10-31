# -*- coding: utf-8 -*-
"""
A SEED — Flask server (Ollama backend) — FINAL VERSION V2 (READABILITY EDITION)

This version keeps the *exact same behavior* as your original server, but it:
- Adds clear docstrings and inline comments in English.
- Highlights the purpose of each section and function.
- Keeps configuration, routes, and logic intact (no functional changes).

Key Features (unchanged):
- User authentication (with display name and password hash)
- Chat endpoint (/api/chat) that proxies to an Ollama backend
- Per-user session management for saving/loading chat histories
- Admin dashboard for runtime stats and a restart button
- Optional GPU info via NVML (if available)

Security/Operational Notes (same as original behavior):
- Session secret, admin user/password, model params, etc. are read from environment variables.
- By default, the app serves with Waitress on 0.0.0.0:8000 (suitable for Windows).
- Ensure you protect this server if exposed beyond a trusted network.
"""
from __future__ import annotations

import os
import sys
import json
import time
import uuid
import re
from pathlib import Path
from datetime import datetime  # imported but not used, kept to avoid logic change
from typing import Dict, Any, List, Optional

import psutil
import requests
from flask import (
    Flask, request, jsonify, session, g, redirect, make_response, render_template
)
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------------
# Optional GPU monitoring (NVML)
# -----------------------------
# We try to import PyNVML safely. If it fails, we simply report no GPU stats.
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

# =========================
# ====== Config & Paths ===
# =========================
# Folder layout used by the app. Everything is relative to this file.
BASE_DIR: Path   = Path(__file__).resolve().parent
DATA_DIR: Path   = BASE_DIR / "data"
SESS_DIR: Path   = DATA_DIR / "sessions"
STATIC_DIR: Path = BASE_DIR / "static"
TRAIN_DIR: Path  = BASE_DIR / "training"
USERS_FILE: Path = DATA_DIR / "users.json"

# Make sure essential folders exist.
for d in (DATA_DIR, SESS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---- Ollama / Model configuration (env-overridable) ----
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL_NAME: str  = os.getenv("MODEL_NAME", "gpt-oss:120b-cloud")
NUM_CTX: int     = int(os.getenv("NUM_CTX", "4096"))
GEN_TEMP: float  = float(os.getenv("GEN_TEMP", "0.7"))
TOP_P: float     = float(os.getenv("TOP_P", "0.9"))

# ---- Admin & Flask secret configuration (env-overridable) ----
ADMIN_USER: str     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY: str     = os.getenv("SECRET_KEY", "a-seed-secret-key-dev")

# ---- Flask App initialization ----
# static_folder/templates: keep paths identical to original behavior.
app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder='templates')
app.secret_key = SECRET_KEY
# Samesite Lax is suitable for most same-origin flows; Secure False is OK for local dev.
app.config.update(SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=False)

# ---- Runtime globals ----
START_TS: float = time.time()
REQUEST_LOGS: List[Dict[str, Any]] = []
MAX_REQ_LOGS: int = 100  # kept for potential future use

# ==================================
# ======= User Auth Utilities =======
# ==================================
def read_users() -> Dict[str, Any]:
    """
    Load the user database from USERS_FILE.

    Returns:
        dict: Mapping of username -> { hash, display_name, created_at }.
    """
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # If the file is empty or invalid JSON, treat as no users yet.
        return {}

def write_users(users: Dict[str, Any]) -> None:
    """
    Persist the user database to USERS_FILE (pretty-printed JSON).
    """
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# =========================
# ======= General Utils ===
# =========================
def now_ts() -> int:
    """Return the current UNIX timestamp (seconds)."""
    return int(time.time())

def safe_json(s: str) -> Dict[str, Any]:
    """
    Try to extract a JSON object from a text blob.
    - Looks for the first {...} span and attempts to json.loads it.
    - If no valid JSON is found, return {}.

    This is useful when the model might embed JSON in a longer reply.
    """
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

def ensure_sid(sid: Optional[str]) -> str:
    """
    Ensure a chat session ID exists.
    - If 'sid' is falsy, return a new UUID4 string.
    """
    return sid or str(uuid.uuid4())

def get_user_session_dir() -> Optional[Path]:
    """
    Get (and create if needed) the folder where the current user's chat sessions live.
    Returns None if there is no authenticated user.
    """
    user_id = session.get('user_id')
    if not user_id:
        return None
    # Keep only safe characters to avoid creating odd filenames.
    safe_user_id = re.sub(r'[^\w-]', '', user_id)
    user_dir = SESS_DIR / safe_user_id
    user_dir.mkdir(exist_ok=True)
    return user_dir

def session_path(sid: str) -> Optional[Path]:
    """
    Build the file path for a specific chat session JSON, scoped to the logged-in user.
    Returns None if we cannot resolve a user dir (i.e., not logged in).
    """
    user_dir = get_user_session_dir()
    safe_sid = re.sub(r'[^\w-]', '', sid)
    return user_dir / f"{safe_sid}.json" if user_dir else None

def write_json(path: Optional[Path], obj: Any) -> None:
    """
    Write JSON atomically:
    - Write to a temporary file first, then replace the target.
    """
    if not path:
        return
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)

def read_json(path: Optional[Path]) -> Any:
    """Read JSON from the given path, returning None if it doesn't exist."""
    if not path or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# =======================================
# ====== Ollama & AI Backend helpers =====
# =======================================
def ollama_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Call the Ollama /api/chat endpoint with the provided message list.

    Args:
        messages: A list of {role: "system"|"user"|"assistant", content: str}

    Returns:
        dict: {"raw": <full response json>, "text": <assistant content string>}

    Raises:
        requests.HTTPError: if the HTTP request failed.
        requests.RequestException: for other network/timeouts, etc.
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model":    MODEL_NAME,
        "messages": messages,
        "stream":   False,  # keep sync mode for simplicity
        "options":  {"num_ctx": NUM_CTX, "temperature": GEN_TEMP, "top_p": TOP_P},
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    content = data.get("message", {}).get("content", "")
    return {"raw": data, "text": content}

def get_system_prompt() -> str:
    """
    Return the system prompt used for all chats.
    If 'training/a_seed_prompt.txt' exists, that custom prompt is used.
    Otherwise, a simple default is returned.
    """
    prompt_file = TRAIN_DIR / "a_seed_prompt.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "You are a helpful and empathetic assistant named A SEED."

# ===========================================
# =========== Auth Pages & API (UNCHANGED) ===
# ===========================================
@app.route("/")
def root():
    """Redirect to /chat if logged in; otherwise to /login."""
    if 'user_id' in session:
        return redirect('/chat')
    return redirect('/login')

@app.route("/chat")
def chat_page():
    """
    Serve the main chat page (index.html).
    - Inject the user's display name into the template for the UI header.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    users = read_users()
    display_name = users.get(user_id, {}).get('display_name', user_id)
    return render_template('index.html', display_name=display_name)

@app.route("/login")
def login_page():
    """Serve the login/register page."""
    return render_template('login.html')

@app.post("/api/register")
def api_register():
    """
    Create a new user:
    - Expects JSON: { username, displayName, password }
    - Returns 409 if username already exists.
    """
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
    """
    Authenticate a user:
    - Expects JSON: { username, password }
    - On success, sets session['user_id'] and session['display_name'].
    """
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
    """Clear any user session and return ok."""
    session.pop('user_id', None)
    session.pop('display_name', None)
    return jsonify({"ok": True})

@app.get("/api/session-check")
def api_session_check():
    """Check if a user session is present (for frontend to gate routes)."""
    return jsonify({"logged_in": 'user_id' in session})

# ===========================================
# =============== Chat API ==================
# ===========================================
@app.post("/api/chat")
def api_chat():
    """
    Proxy a user message to the Ollama backend and return an assistant reply.
    - Requires an authenticated user.
    - Accepts JSON: { message: str, history: [{role, text}] }
    - System prompt is prepended; history is rehydrated into (role,content) pairs.
    - Attempts to parse a JSON object from model output; falls back to raw text.
    """
    if 'user_id' not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    user_msg = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_msg:
        return jsonify({"error": "empty-message"}), 400

    sys_prompt = get_system_prompt()

    # Rebuild conversation for the model: system -> history -> current user turn
    msgs = [{"role": "system", "content": sys_prompt}]
    for turn in history:
        if turn.get('role') in ['user', 'assistant']:
            msgs.append({"role": turn['role'], "content": turn['text']})
    msgs.append({"role": "user", "content": user_msg})

    try:
        out = ollama_chat(msgs)
        text = out.get("text") or ""
    except Exception as e:
        # If backend fails (network, timeout, etc.), surface a 500 so UI can react.
        return jsonify({"error": "backend-failed", "hint": str(e)}), 500

    # If the model returns a JSON blob like {"reply": "...", "emotion": "..."}, extract it.
    obj = safe_json(text)
    reply = (obj.get("reply") or text.strip() or
             "I'm not sure how to respond to that. Could you rephrase?").strip()
    emo = (obj.get("emotion") or "neutral").lower().strip()

    return jsonify({"emotion": emo, "reply": reply})

# ===========================================
# ========= Sessions Save/Load etc ==========
# ===========================================
@app.post("/api/save")
def api_save():
    """
    Save the current chat under a session file scoped to the user.
    - Expects JSON: { sid?, chat: [{role, text}, ...] }
    - If no 'sid' is provided, a new one is generated.
    - Title is derived from the first user message (first 60 chars).
    """
    if 'user_id' not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    sid = ensure_sid(data.get("sid"))
    chat = data.get("chat") or []
    path = session_path(sid)

    if path:
        # Human-friendly title: first user message if present, else "New Chat"
        first_user_message = next((item['text'] for item in chat if item['role'] == 'user'), "New Chat")
        title = first_user_message[:60]

        write_json(path, {"sid": sid, "title": title, "chat": chat, "updated": now_ts()})
        return jsonify({"ok": True, "sid": sid, "title": title})
    return jsonify({"ok": False, "error": "could_not_get_session_path"}), 500

@app.get("/api/sessions")
def api_sessions():
    """
    List available chat sessions for the logged-in user.
    Returns minimal metadata for each session: sid, title, message count, last updated.
    """
    if 'user_id' not in session:
        return jsonify({"error": "unauthorized"}), 401

    user_dir = get_user_session_dir()
    if not user_dir:
        return jsonify([])

    res: List[Dict[str, Any]] = []
    for p in user_dir.glob("*.json"):
        try:
            obj = read_json(p) or {}
            res.append({
                "sid": obj.get("sid") or p.stem,
                "title": obj.get("title") or p.stem,
                "count": len(obj.get("chat") or []),
                "updated": obj.get("updated") or int(p.stat().st_mtime),
            })
        except Exception:
            # Skip files that fail to parse, but never crash the endpoint.
            pass

    # Most recent first
    res.sort(key=lambda x: x["updated"], reverse=True)
    return jsonify(res)

@app.get("/api/load")
def api_load():
    """
    Load a specific chat session JSON:
    - Querystring: ?sid=<session_id>
    """
    if 'user_id' not in session:
        return jsonify({"error": "unauthorized"}), 401

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
def nvidia_query() -> Optional[List[Dict[str, Any]]]:
    """
    If NVML is available, return a list of per-GPU stats:
    - name, total/used memory (MB), utilization (%)
    Returns None if NVML is not available or any error occurs.
    """
    if not NVML_AVAILABLE:
        return None
    try:
        gpus: List[Dict[str, Any]] = []
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

def safe_ollama_get(path: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Helper to GET against the Ollama server. Returns parsed JSON or None on failure.
    """
    try:
        r = requests.get(OLLAMA_HOST + path, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@app.route("/admin")
def admin_page():
    """
    Serve the admin login page unless already authenticated as admin.
    """
    if session.get("admin"):
        return redirect("/admin/dashboard")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    """Serve the admin dashboard page (requires admin session)."""
    if not session.get("admin"):
        return redirect("/admin")
    return render_template("admin.html")

@app.post("/api/admin/login")
def admin_login():
    """
    Admin login:
    - Expects JSON { username, password }
    - Compares to env-provided ADMIN_USER / ADMIN_PASSWORD
    - Sets session["admin"] on success.
    """
    data = request.get_json()
    if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401

@app.post("/api/admin/logout")
def admin_logout():
    """Clear admin session and return ok."""
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.get("/api/admin/status")
def admin_status():
    """Simple helper for the frontend to know if admin is logged in."""
    return jsonify({"logged_in": bool(session.get("admin"))})

@app.post("/api/admin/restart")
def api_restart():
    """
    Attempt to restart the current Python process using os.execv.
    - Only allowed for admin sessions.
    - If execv fails, return a descriptive error.
    """
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401

    print("--- SERVER RESTART INITIATED BY ADMIN ---", flush=True)

    try:
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    # If execv succeeds, the process image is replaced (no return).
    return jsonify({"ok": True})

@app.get("/api/stats")
def api_stats():
    """
    Provide a snapshot of system/runtime status for the admin dashboard:
    - Basic CPU/RAM/process info via psutil
    - Ollama model list presence
    - Optional GPU info via NVML
    """
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 401

    now = time.time()
    mem = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())

    # Ask Ollama for the available models.
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
    # Host '0.0.0.0' allows access from other devices on the same network (e.g., your phone).
    host = "0.0.0.0"
    port = 8000

    def print_network_info() -> None:
        """
        Print a friendly hint showing your local IP so you can test from your phone.
        Falls back to a generic note if network info fails.
        """
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

    # Use Waitress, a production-ready WSGI server that works well on Windows.
    from waitress import serve
    print(f"   - Server is live. Press Ctrl+C in this window to stop.", flush=True)
    serve(app, host=host, port=port)
