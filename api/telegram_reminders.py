import os
import json
import time
import threading
import requests
import datetime
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_UID = os.getenv("TELEGRAM_ALLOWED_UID")

REMINDERS_FILE = "reminders.json"
REMINDER_LOCK = threading.Lock()

def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r") as f:
            data = json.load(f)
            # Convert string times back to datetime objects
            for r in data:
                r["time"] = datetime.datetime.fromisoformat(r["time"])
            return data
    except Exception as e:
        print(f"[!] Error loading reminders: {e}")
        return []

def save_reminders(reminders):
    try:
        with open(REMINDERS_FILE, "w") as f:
            # Convert datetime objects to ISO strings for JSON serialization
            data = [{"time": r["time"].isoformat(), "message": r["message"]} for r in reminders]
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[!] Error saving reminders: {e}")

REMINDERS = load_reminders()

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALLOWED_UID:
        print("[!] Telegram credentials missing in .env")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_ALLOWED_UID,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"[*] Scheduled Telegram reminder sent: {message}")
    except Exception as e:
        print(f"[!] Failed to send Telegram reminder: {e}")

def schedule_telegram_reminder(message, datetime_str):
    """
    Schedules a one-time reminder to be sent via Telegram.
    datetime_str should be in 'YYYY-MM-DD HH:MM' format.
    If only 'HH:MM' is provided, it assumes today.
    """
    try:
        if len(datetime_str.split()) == 1:
            # Only time provided, assume today
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            datetime_str = f"{today} {datetime_str}"
            
        dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        
        if dt < datetime.datetime.now():
            return f"Cannot schedule reminder in the past! Current time is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}."

        with REMINDER_LOCK:
            REMINDERS.append({"time": dt, "message": message})
            REMINDERS.sort(key=lambda x: x["time"])
            save_reminders(REMINDERS)
            
        return f"Successfully scheduled Telegram reminder for {datetime_str}: '{message}'"
    except ValueError:
        return f"Failed to schedule reminder. Invalid datetime format. Please use 'YYYY-MM-DD HH:MM' or 'HH:MM'."
    except Exception as e:
        return f"Failed to schedule reminder: {e}"

def get_scheduled_reminders():
    """Returns a list of all currently scheduled reminders."""
    with REMINDER_LOCK:
        if not REMINDERS:
            return "No active reminders are currently scheduled."
        
        result = "Active Reminders:\n"
        for idx, r in enumerate(REMINDERS):
            next_run = r["time"].strftime("%Y-%m-%d %H:%M:%S")
            message = r["message"]
            result += f"{idx + 1}. At {next_run}: '{message}'\n"
        return result

def cancel_telegram_reminder(reminder_index):
    """
    Cancels a reminder based on its index (1-based) returned by get_scheduled_reminders.
    """
    with REMINDER_LOCK:
        if not REMINDERS:
            return "No active reminders to cancel."
        
        try:
            idx = int(reminder_index) - 1
            if idx < 0 or idx >= len(REMINDERS):
                return f"Invalid index. Please provide a number between 1 and {len(REMINDERS)}."
            
            job_to_cancel = REMINDERS.pop(idx)
            save_reminders(REMINDERS)
            return f"Successfully cancelled reminder #{reminder_index}."
        except Exception as e:
            return f"Failed to cancel reminder: {e}"

def run_scheduler():
    """Background loop for the scheduler."""
    while True:
        now = datetime.datetime.now()
        reminders_to_fire = []
        
        with REMINDER_LOCK:
            # Find all reminders that are due or past due
            for r in REMINDERS[:]:
                if r["time"] <= now:
                    reminders_to_fire.append(r)
                    REMINDERS.remove(r)
            if reminders_to_fire:
                save_reminders(REMINDERS)
                    
        # Fire them outside the lock to avoid blocking other operations
        for r in reminders_to_fire:
            send_telegram_message(r["message"])
            
        time.sleep(1)

def start_telegram_scheduler():
    """Starts the background thread for telegram reminders."""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[*] Telegram Background Scheduler started (Persistent JSON Engine).")
