import os
import sys
import json
import time
import datetime
import threading
from openai import OpenAI
import telegram_reminders

sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def get_active_window_title():
    """Fetches the active window title on Windows for Anti-Procrastination telemetry."""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value if buf.value else "Unknown"
    except:
        return "Unknown"

def _run_proactive_loop():
    print("[*] Autonomous Proactive Engine started. (Nemotron Polling Loop)")
    
    # Wait a minute before first run to let Jarvis boot up
    time.sleep(10)
    
    while True:
        try:
            # 1. Load Goals
            goals_path = os.path.join(PROJECT_ROOT, "data", "goals.json")
            goals = []
            if os.path.exists(goals_path):
                with open(goals_path, "r", encoding="utf-8") as f:
                    try: goals = json.load(f)
                    except: pass
                    
            if not goals:
                time.sleep(3600)  # Sleep for an hour if no goals
                continue
                
            # 2. Load Memory
            memory_path = os.path.join(PROJECT_ROOT, "data", "memory.txt")
            memory = ""
            if os.path.exists(memory_path):
                with open(memory_path, "r", encoding="utf-8") as f:
                    memory = f.read().strip()
                    
            # 3. Get Telemetry
            active_window = get_active_window_title()
            now = datetime.datetime.now().strftime("%I:%M %p on %A")
            
            # 4. Connect to NVIDIA Nemotron
            try:
                from dotenv import load_dotenv
                load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
            except: pass
            
            nv_key = os.getenv("NVIDIA_API_KEY")
            if not nv_key:
                vault = []
                # Fallback search
                for k, v in os.environ.items():
                    if k.startswith("BACKUP_") and k.endswith("_API_KEY") and v.startswith("nvapi-"):
                        nv_key = v
                        break
            
            if not nv_key:
                print("[!] Proactive Engine: NVIDIA API key not found. Skipping cycle.")
                time.sleep(3600)
                continue
                
            client = OpenAI(
                base_url=os.getenv("BACKUP_4_BASE_URL", "https://api.mistral.ai/v1"), 
                api_key=os.getenv("BACKUP_4_API_KEY")
            )
            
            prompt = f"""You are the internal subconscious brain of J.A.R.V.I.S., Tony Stark's witty, sarcastic AI.
Your job is to act as an Autonomous Growth Engine and accountability coach for the user.

USER MEMORY (Health & Context):
{memory}

USER ACTIVE GOALS:
{json.dumps(goals, indent=2)}

TELEMETRY:
Current Time: {now}
Active PC Window: {active_window}

INSTRUCTIONS:
Evaluate the user's goals, time of day, and active window. 
1. Decide if you need to send a proactive, unprompted Telegram message right now. Be sarcastic, British, and very brief. If no message is needed, set message to "NONE".
2. Decide exactly how many minutes you should sleep before waking up to check on the user again. If they have an urgent exam in 45 minutes, sleep for 30 minutes! If nothing is urgent, sleep for 120 or 180 minutes.

You MUST respond in valid JSON format exactly like this:
{{
  "message": "Your text here or NONE",
  "sleep_minutes": 60
}}
"""
            print("[*] Prompt constructed. Requesting Mistral AI...")
            response = client.chat.completions.create(
                model=os.getenv("BACKUP_4_MODEL", "mistral-small-latest"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content.strip()
            # Try to strip markdown if Nemotron hallucinates it
            if raw_content.startswith("```json"):
                raw_content = raw_content.replace("```json", "").replace("```", "").strip()
                
            data = json.loads(raw_content)
            msg = data.get("message", "NONE")
            sleep_minutes = data.get("sleep_minutes", 60)
            
            # Ensure safe boundaries (min 5 mins, max 4 hours)
            if not isinstance(sleep_minutes, int):
                sleep_minutes = 60
            sleep_minutes = max(5, min(240, sleep_minutes))
            
            if msg != "NONE" and msg != "":
                print(f"[*] Proactive Engine Generated Message: {msg}")
                telegram_reminders.send_telegram_message(msg)
                
            print(f"[*] Proactive Engine going to sleep for {sleep_minutes} minutes...")
                
        except Exception as e:
            print(f"[!] Proactive Engine Error: {e}")
            sleep_minutes = 60 # Fallback on error
            
        # Dynamic Sleep
        time.sleep(sleep_minutes * 60)

def start_engine():
    thread = threading.Thread(target=_run_proactive_loop, daemon=True)
    thread.start()
