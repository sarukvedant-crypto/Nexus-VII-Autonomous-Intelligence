import os
import sys
import json
import asyncio
import threading
import uuid
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
import base64
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from google import genai

# Ensure imports work from jarvis_assistant directory
sys.path.insert(0, os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
from jarvis_local import JarvisEngine, UniversalAI, get_system_telemetry, get_config
from api.telegram_bot import start_telegram_bot
from vector_memory import get_memory

# ============================================================
# APP SETUP
# ============================================================
app = FastAPI(title="J.A.R.V.I.S. HUD")

STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ============================================================
# GLOBAL STATE
# ============================================================
engine = JarvisEngine()
ws_clients: set[WebSocket] = set()
transcript_log: list[dict] = []

# Confirmation gate state
_pending_confirmations = {}  # id -> threading.Event
_confirmation_results = {}   # id -> bool

async def broadcast(msg: dict):
    """Send a JSON message to all connected WebSocket clients."""
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(msg)
        except:
            dead.add(ws)
    ws_clients.difference_update(dead)

# Bridge from sync engine callbacks to async broadcast
_loop = None

def _broadcast_sync(msg: dict):
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast(msg), _loop)

def on_status(status):
    _broadcast_sync({"type": "status", "data": status})

def on_transcript(role, text):
    entry = {"role": role, "text": text}
    transcript_log.append(entry)
    _broadcast_sync({"type": "transcript", "data": entry})

def on_log(msg):
    _broadcast_sync({"type": "log", "data": msg})

def request_confirmation(tool_name, args):
    """Blocks the calling thread until the user confirms or denies via the HUD."""
    confirm_id = str(uuid.uuid4())
    event = threading.Event()
    _pending_confirmations[confirm_id] = event
    _confirmation_results[confirm_id] = False
    
    _broadcast_sync({
        "type": "confirm",
        "id": confirm_id,
        "tool": tool_name,
        "args": args
    })
    
    # Block until user responds (timeout after 60 seconds)
    event.wait(timeout=60)
    
    result = _confirmation_results.pop(confirm_id, False)
    _pending_confirmations.pop(confirm_id, None)
    return result

def on_model_change(model):
    _broadcast_sync({"type": "model_change", "data": model})

engine.on_status = on_status
engine.on_transcript = on_transcript
engine.on_log = on_log
engine.on_model_change = on_model_change
engine.ai.on_confirm_request = request_confirmation

# ============================================================
# ROUTES
# ============================================================
@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """Handles media file uploads from the chat interface."""
    import time
    ext = os.path.splitext(file.filename)[1] or '.png'
    safe_name = f"upload_{int(time.time() * 1000)}{ext}"
    save_path = os.path.join(UPLOADS_DIR, safe_name)
    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)
    return {"ok": True, "url": f"/static/uploads/{safe_name}", "path": save_path}

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/api/status")
async def api_status():
    return {"running": engine.running}

@app.post("/api/start")
async def api_start():
    engine.start()
    return {"ok": True}

@app.post("/api/stop")
async def api_stop():
    engine.stop()
    return {"ok": True}

@app.post("/api/interrupt")
async def api_interrupt():
    engine.interrupt()
    return {"ok": True}

@app.get("/api/telemetry")
async def api_telemetry():
    t = get_system_telemetry()
    return {
        "cpu": t["cpu"],
        "ram_pct": t["ram_pct"],
        "ram_used": t["ram_used"],
        "ram_total": t["ram_total"],
        "power": t["power"],
        "power_pct": t["power_pct"],
        "time": t["time"],
        "weather": t["weather"],
    }

@app.post("/api/memory/add")
async def api_memory_add(
    text: str = Form(""),
    file: UploadFile | None = File(None)
):
    try:
        vmem = get_memory()
        if not vmem:
            return JSONResponse(status_code=500, content={"error": "Vector memory not initialized."})
            
        final_text = text.strip()
        
        # If an image is provided, use NVIDIA Llama 3.2 90B Vision to describe it
        if file and file.filename:
            try:
                import requests
                img_data = await file.read()
                b64_data = base64.b64encode(img_data).decode('utf-8')
                mime_type = file.content_type or "image/png"
                
                
                keys_to_try = []
                gemini_key = os.getenv("GEMINI_API_KEY", "")
                if gemini_key and (gemini_key.startswith("AQ.") or gemini_key.startswith("AIza")):
                    keys_to_try.append(gemini_key)
                for i in range(1, 11):
                    bk = os.getenv(f"BACKUP_{i}_API_KEY", "")
                    if bk and (bk.startswith("AQ.") or bk.startswith("AIza")) and bk not in keys_to_try:
                        keys_to_try.append(bk)

                if not keys_to_try:
                    return JSONResponse(status_code=500, content={"error": "No valid Gemini API key found for vision."})

                vision_desc = ""
                for key in keys_to_try:
                    try:
                        client = genai.Client(api_key=key)
                        response = client.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=[
                                {
                                    "parts": [
                                        {"text": text or "Describe this image in detail so I can remember it."},
                                        {"inline_data": {"mime_type": file.content_type or "image/jpeg", "data": img_data}}
                                    ]
                                }
                            ]
                        )
                        vision_desc = response.text
                        break
                    except:
                        continue
                
                if vision_desc:
                    final_text = f"[Image Memory] User's Note: {text}\nVisual Description: {vision_desc}" if text else f"[Image Memory] Visual Description: {vision_desc}"
                else:
                    return JSONResponse(status_code=500, content={"error": "Vision analysis failed."})
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": f"Failed to process image: {e}"})
                
        if not final_text:
            return JSONResponse(status_code=400, content={"error": "No valid text or image provided."})
            
        res = vmem.remember(final_text)
        if "already exists" in res.lower() or "too short" in res.lower():
            return JSONResponse(status_code=400, content={"error": res})
            
        return {"status": "success", "message": "Memory permanently stored in neural vault."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/transcript")
async def api_transcript():
    return transcript_log

@app.get("/api/settings")
async def api_get_settings():
    cfg = get_config()
    memory = ""
    try:
        vmem = get_memory()
        if vmem and vmem.is_seeded():
            memory = vmem.get_all_formatted()
        else:
            with open(os.path.join(PROJECT_ROOT, "data", "memory.txt"), "r", encoding="utf-8") as f:
                memory = f.read()
    except:
        try:
            with open(os.path.join(PROJECT_ROOT, "data", "memory.txt"), "r", encoding="utf-8") as f:
                memory = f.read()
        except: pass
    return {
        "AI_BASE_URL": cfg["AI_BASE_URL"],
        "AI_API_KEY": cfg["AI_API_KEY"],
        "AI_MODEL": cfg["AI_MODEL"],
        "AI_VOICE": os.getenv("AI_VOICE", "en-GB-RyanNeural"),
        "BACKUP_1_BASE_URL": os.getenv("BACKUP_1_BASE_URL", ""),
        "BACKUP_1_API_KEY": os.getenv("BACKUP_1_API_KEY", ""),
        "BACKUP_1_MODEL": os.getenv("BACKUP_1_MODEL", ""),
        "BACKUP_2_BASE_URL": os.getenv("BACKUP_2_BASE_URL", ""),
        "BACKUP_2_API_KEY": os.getenv("BACKUP_2_API_KEY", ""),
        "BACKUP_2_MODEL": os.getenv("BACKUP_2_MODEL", ""),
        "GMAIL_ADDRESS": os.getenv("GMAIL_ADDRESS", ""),
        "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD", ""),
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "TELEGRAM_ALLOWED_UID": os.getenv("TELEGRAM_ALLOWED_UID", ""),
        "memory": memory,
    }

class SettingsUpdate(BaseModel):
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_VOICE: str = ""
    memory: str | None = None
    BACKUP_1_BASE_URL: str = ""
    BACKUP_1_API_KEY: str = ""
    BACKUP_1_MODEL: str = ""
    BACKUP_2_BASE_URL: str = ""
    BACKUP_2_API_KEY: str = ""
    BACKUP_2_MODEL: str = ""
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_UID: str = ""

@app.post("/api/settings")
async def api_update_settings(body: SettingsUpdate):
    env_path = os.path.join(PROJECT_ROOT, ".env")

    # Read existing .env and update values
    lines = []
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except: pass

    def set_env_value(lines, key, value):
        found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f'{key}="'):
                lines[i] = f'{key}="{value}"\n'
                found = True
                break
        if not found:
            lines.append(f'{key}="{value}"\n')
        return lines

    if body.AI_BASE_URL:
        lines = set_env_value(lines, "AI_BASE_URL", body.AI_BASE_URL)
    if body.AI_API_KEY:
        lines = set_env_value(lines, "AI_API_KEY", body.AI_API_KEY)
    if body.AI_MODEL:
        lines = set_env_value(lines, "AI_MODEL", body.AI_MODEL)
    if body.AI_VOICE:
        lines = set_env_value(lines, "AI_VOICE", body.AI_VOICE)

    # Backup providers
    if body.BACKUP_1_BASE_URL:
        lines = set_env_value(lines, "BACKUP_1_BASE_URL", body.BACKUP_1_BASE_URL)
    if body.BACKUP_1_API_KEY:
        lines = set_env_value(lines, "BACKUP_1_API_KEY", body.BACKUP_1_API_KEY)
    if body.BACKUP_1_MODEL:
        lines = set_env_value(lines, "BACKUP_1_MODEL", body.BACKUP_1_MODEL)
    if body.BACKUP_2_BASE_URL:
        lines = set_env_value(lines, "BACKUP_2_BASE_URL", body.BACKUP_2_BASE_URL)
    if body.BACKUP_2_API_KEY:
        lines = set_env_value(lines, "BACKUP_2_API_KEY", body.BACKUP_2_API_KEY)
    if body.BACKUP_2_MODEL:
        lines = set_env_value(lines, "BACKUP_2_MODEL", body.BACKUP_2_MODEL)
    # Gmail
    if body.GMAIL_ADDRESS:
        lines = set_env_value(lines, "GMAIL_ADDRESS", body.GMAIL_ADDRESS)
    if body.GMAIL_APP_PASSWORD:
        lines = set_env_value(lines, "GMAIL_APP_PASSWORD", body.GMAIL_APP_PASSWORD)
    # Telegram
    if body.TELEGRAM_BOT_TOKEN:
        lines = set_env_value(lines, "TELEGRAM_BOT_TOKEN", body.TELEGRAM_BOT_TOKEN)
    if body.TELEGRAM_ALLOWED_UID:
        lines = set_env_value(lines, "TELEGRAM_ALLOWED_UID", body.TELEGRAM_ALLOWED_UID)

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    if body.memory is not None:
        with open(os.path.join(PROJECT_ROOT, "data", "memory.txt"), "w", encoding="utf-8") as f:
            f.write(body.memory)
        # Also sync to vector memory if available
        try:
            vmem = get_memory()
            if vmem and vmem.is_ready():
                vmem.clear_all()
                vmem.seed_from_file()
        except: pass

    # Reinitialize the AI client with fresh config
    from dotenv import load_dotenv
    load_dotenv(override=True)
    engine.ai.reinit()

    return {"ok": True, "message": "Settings saved and AI reinitialized."}

@app.get("/api/list_skills")
def list_skills():
    skills_dir = os.path.join(PROJECT_ROOT, "skills")
    if not os.path.exists(skills_dir):
        return {"status": "success", "skills": []}
    
    files = []
    for f in os.listdir(skills_dir):
        if f.endswith(".md") or f.endswith(".txt"):
            try:
                with open(os.path.join(skills_dir, f), "r", encoding="utf-8") as file:
                    content = file.read()
                files.append({"name": f, "content": content})
            except:
                pass
    return {"status": "success", "skills": files}

class ImportSkillURL(BaseModel):
    url: str
    name: str

@app.post("/api/import_skill_url")
def import_skill_url(body: ImportSkillURL):
    try:
        import requests
        res = requests.get(body.url, timeout=10)
        res.raise_for_status()
        
        filename = body.name
        if not filename.endswith(".md") and not filename.endswith(".txt"):
            filename += ".md"
            
        skills_dir = os.path.join(PROJECT_ROOT, "skills")
        os.makedirs(skills_dir, exist_ok=True)
        
        with open(os.path.join(skills_dir, filename), "w", encoding="utf-8") as f:
            f.write(res.text)
            
        return {"status": "success", "message": f"Imported {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/upload_skill")
async def upload_skill(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename
        
        skills_dir = os.path.join(PROJECT_ROOT, "skills")
        os.makedirs(skills_dir, exist_ok=True)
        
        with open(os.path.join(skills_dir, filename), "wb") as f:
            f.write(content)
            
        return {"status": "success", "message": f"Uploaded {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class DeleteSkill(BaseModel):
    name: str

@app.post("/api/delete_skill")
def delete_skill(body: DeleteSkill):
    try:
        skills_dir = os.path.join(PROJECT_ROOT, "skills")
        filepath = os.path.join(skills_dir, body.name)
        if os.path.exists(filepath):
            os.remove(filepath)
            return {"status": "success"}
        return {"status": "error", "message": "File not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================================
# WEBSOCKET
# ============================================================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    # Send current status
    initial_status = "STANDBY" if engine.running else "OFFLINE"
    await ws.send_json({"type": "status", "data": initial_status})
    # Send current model
    await ws.send_json({"type": "model_change", "data": engine.ai._current_model})
    # Send existing transcript
    for entry in transcript_log:
        await ws.send_json({"type": "transcript", "data": entry})
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "start":
                engine.start()
            elif msg.get("action") == "stop":
                engine.stop()
            elif msg.get("action") == "interrupt":
                engine.interrupt()
            elif msg.get("action") == "chat":
                text = msg.get("text", "").strip()
                media_path = msg.get("media_path", None)
                
                # Check for authorization override
                if text.lower() == "jarvis is freaky" and _pending_confirmations:
                    for cid, event in list(_pending_confirmations.items()):
                        _confirmation_results[cid] = True
                        event.set()
                    on_transcript("user", text)
                    on_transcript("log", "[✓] Secret passphrase accepted. Authorization granted.")
                    continue
                    
                if text or media_path:
                    threading.Thread(target=engine.send_text, args=(text, media_path), daemon=True).start()
            elif msg.get("action") == "confirm_response":
                confirm_id = msg.get("id")
                approved = msg.get("approved", False)
                if confirm_id in _pending_confirmations:
                    _confirmation_results[confirm_id] = approved
                    _pending_confirmations[confirm_id].set()
    except WebSocketDisconnect:
        ws_clients.discard(ws)

# ============================================================
# STARTUP
# ============================================================
@app.on_event("startup")
async def startup_event():
    global _loop
    _loop = asyncio.get_running_loop()
    # Start Telegram bot if configured
    try:
        start_telegram_bot(engine.ai)
    except Exception as e:
        print(f"[!] Telegram bot failed to start: {e}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  J.A.R.V.I.S. HUD SERVER")
    print("  Open http://localhost:8000 in your browser")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
