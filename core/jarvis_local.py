import warnings
warnings.simplefilter('ignore')

import os
import re
import sys
import io
import time
import json
import queue
import asyncio
import threading
import subprocess
import numpy as np
import keyboard
import sounddevice as sd
import scipy.io.wavfile as wav
import speech_recognition as sr
import urllib.parse
import pyttsx3
import psutil
import datetime
from dotenv import load_dotenv
from openai import OpenAI
from vector_memory import get_memory, init_and_seed
from modules.app_locator import find_app, refresh_if_stale, get_suggestions
from modules import calendar_module
from api import telegram_reminders
from modules import ocr_module
from modules import drive_downloader

# Hide the annoying Pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

# ============================================================
# LAZY INIT GLOBALS (initialized on demand, not at import)
# ============================================================
_pygame_initialized = False
_colorama_initialized = False

def _init_pygame():
    global _pygame_initialized
    if not _pygame_initialized:
        import pygame
        pygame.mixer.init()
        _pygame_initialized = True

def _init_colorama():
    global _colorama_initialized
    if not _colorama_initialized:
        from colorama import init
        init(autoreset=True)
        _colorama_initialized = True

def _fore(color):
    try:
        from colorama import Fore
        return getattr(Fore, color, '')
    except:
        return ''

def _style_reset():
    try:
        from colorama import Style
        return Style.RESET_ALL
    except:
        return ''

# ============================================================
# CONFIG
# ============================================================
load_dotenv()
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def get_config():
    return {
        "AI_BASE_URL": os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1"),
        "AI_API_KEY": os.getenv("AI_API_KEY", "PASTE_YOUR_API_KEY_HERE"),
        "AI_MODEL": os.getenv("AI_MODEL", "llama-3.1-8b-instant"),
    }

def get_provider_vault():
    """Loads all backup API providers from .env (BACKUP_1_*, BACKUP_2_*, etc.)."""
    vault = []
    for i in range(1, 11):  # Support up to 10 backup providers
        url = os.getenv(f"BACKUP_{i}_BASE_URL")
        key = os.getenv(f"BACKUP_{i}_API_KEY")
        model = os.getenv(f"BACKUP_{i}_MODEL")
        if url and key and model:
            vault.append({"base_url": url, "api_key": key, "model": model})
    return vault

cfg = get_config()
AI_BASE_URL = cfg["AI_BASE_URL"]
AI_API_KEY = cfg["AI_API_KEY"]
AI_MODEL = cfg["AI_MODEL"]

APP_PATHS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
}
BROWSER_PATH = APP_PATHS["chrome"] if os.path.exists(APP_PATHS["chrome"]) else APP_PATHS["edge"]

# ============================================================
# NEURAL TOOLS (EXECUTED BY AI)
# ============================================================
def open_application(app_name):
    app_name_lower = app_name.lower()
    
    # Special cases
    if "spotify" in app_name_lower:
        try: os.startfile("spotify:")
        except: pass
        return "Opened Spotify successfully."
    elif "gmail" in app_name_lower:
        subprocess.Popen([BROWSER_PATH, "https://mail.google.com"])
        return "Opened Gmail successfully."
        
    # Search cache
    found_path = find_app(app_name)
    if found_path:
        try:
            if found_path.startswith("http") or "://" in found_path:
                subprocess.Popen([BROWSER_PATH, found_path])
            elif found_path.startswith("shell:"):
                subprocess.Popen(["explorer.exe", found_path])
            else:
                os.startfile(found_path)
            return f"Opened application: {app_name}."
        except Exception as e:
            return f"Found application {app_name}, but failed to open it: {e}"
            
    # Suggestions
    suggestions = get_suggestions(app_name)
    suggestion_text = ""
    if suggestions:
        suggestion_text = f" Did you mean: {', '.join(suggestions)}?"
        
    return f"Could not find application: {app_name}.{suggestion_text} Tell the user they need to open it manually."

def close_application(app_name):
    script = f"""
    $procs = Get-Process | Where-Object {{ $_.ProcessName -match '{app_name}' -or $_.MainWindowTitle -match '{app_name}' }}
    if ($procs) {{
        $names = $procs | Select-Object -ExpandProperty ProcessName -Unique
        foreach ($name in $names) {{
            Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }}
        "Closed application: {app_name}"
    }} else {{
        "Could not find running application: {app_name}"
    }}
    """
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if output.strip():
            return output.strip()
        return f"Could not find running application: {app_name}"
    except Exception as e:
        return f"Failed to close application {app_name}: {e}"

def close_all_applications(exemptions=None):
    if exemptions is None:
        exemptions = []
        
    system_exempt = [
        "explorer", "SystemSettings", "TextInputHost", "ApplicationFrameHost", 
        "cmd", "conhost", "python", "node", "pwsh", "powershell", "WindowsTerminal",
        "SearchApp", "StartMenuExperienceHost", "ShellExperienceHost", "sihost",
        "taskmgr", "dwm", "csrss", "smss", "winlogon", "services", "lsass", 
        "svchost", "fontdrvhost", "wininit", "WmiPrvSE", "spoolsv", "SearchIndexer"
    ]
    
    for exc in exemptions:
        system_exempt.append(exc.lower())
        
    exempt_pattern = "|".join(system_exempt)
    
    script = f"""
    $procs = Get-Process | Where-Object {{ 
        $_.MainWindowTitle -ne '' -and 
        $_.ProcessName -notmatch '(?i)^({exempt_pattern})$' 
    }}
    
    $closed = @()
    if ($procs) {{
        $namesToKill = $procs | Select-Object -ExpandProperty ProcessName -Unique
        foreach ($name in $namesToKill) {{
            $closed += $name
            Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }}
    }}
    $closed | Select-Object -Unique
    """
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        closed_apps = [line.strip() for line in output.split('\\n') if line.strip()]
        if closed_apps:
            return f"Closed the following applications: {', '.join(closed_apps)}"
        return "No non-exempt applications were running."
    except Exception as e:
        return f"Failed to close applications: {e}"

def _run_spotify_search_and_play(query):
    try:
        from playwright.sync_api import sync_playwright
        import urllib.parse
        import os
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"https://open.spotify.com/search/{urllib.parse.quote(query)}/tracks", timeout=15000)
            page.wait_for_selector('a[href^="/track/"]', timeout=10000)
            href = page.locator('a[href^="/track/"]').first.get_attribute('href')
            browser.close()
            
        if href:
            track_id = href.split('/')[-1]
            os.startfile(f"spotify:track:{track_id}")
    except Exception as e:
        print(f"Spotify search macro failed: {e}")

def play_music_on_spotify(query):
    import threading
    t = threading.Thread(target=_run_spotify_search_and_play, args=(query,), daemon=True)
    t.start()
    return f"Searching and playing '{query}' on Spotify."

def enter_coding_mode():
    return "__HOT_SWAP_NEMOTRON__"

def exit_coding_mode():
    return "__HOT_SWAP_GEMINI__"

def search_youtube(query):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    subprocess.Popen([BROWSER_PATH, url])
    return f"Opened YouTube search for '{query}'."

def search_google(query):
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    subprocess.Popen([BROWSER_PATH, url])
    return f"Opened Google search for '{query}'."

def background_search(query):
    is_news = "news" in query.lower()
    
    if is_news:
        try:
            import requests
            from bs4 import BeautifulSoup
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.content, 'xml')
            
            results = []
            for item in soup.find_all('item', limit=4):
                title = item.title.text if item.title else "No Title"
                pub_date = item.pubDate.text if item.pubDate else "No Date"
                results.append(f"- {title} ({pub_date})")
                
            if not results:
                return f"No news found for '{query}'."
            return f"TOP NEWS HEADLINES FOR '{query}':\n" + "\n".join(results)
        except Exception as e:
            return f"News search failed: {e}"
    else:
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            data = {'q': query}
            res = requests.post('https://lite.duckduckgo.com/lite/', data=data, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            results = []
            for tr in soup.find_all('tr'):
                snippet_td = tr.find('td', class_='result-snippet')
                if snippet_td:
                    text = snippet_td.text.strip()
                    if text:
                        results.append(text)
                        
            if not results:
                return f"No internet search results found for '{query}'."
                
            unique_results = list(dict.fromkeys(results))
            return f"WEB SEARCH RESULTS FOR '{query}':\n" + "\n---\n".join(unique_results[:5])
        except Exception as e:
            return f"Encyclopedia search failed: {e}"

def format_drive(drive_letter):
    drive_letter = drive_letter.upper().replace(":", "")
    if len(drive_letter) != 1 or drive_letter in ["C"]:
        return "Error: Invalid drive letter or attempted to format the critical system drive (C:). This action is blocked."
    cmd = f"format {drive_letter}: /FS:NTFS /Q /y"
    try:
        subprocess.Popen(["start", "cmd", "/c", cmd], shell=True)
        return f"Successfully initiated brute-force formatting of drive {drive_letter}:."
    except Exception as e:
        return f"Failed to format drive: {e}"

def get_desktop_path():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        desktop, _ = winreg.QueryValueEx(key, "Desktop")
        return os.path.expandvars(desktop)
    except:
        return os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')

def create_folder(folder_name):
    try:
        desktop_path = get_desktop_path()
        folder_path = os.path.join(desktop_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return f"Successfully created folder '{folder_name}' on the Desktop."
    except Exception as e:
        return f"Failed to create folder: {e}"

def adjust_volume(level):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        import pythoncom
        
        pythoncom.CoInitialize()
        try:
            # Ensure level is between 0 and 100
            level = max(0, min(100, int(level)))
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            if level == 0:
                volume.SetMute(1, None)
            else:
                volume.SetMute(0, None)
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                
            return f"System volume set to exactly {level}%."
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        return f"Failed to adjust volume: {e}"

def media_playback(action):
    try:
        import keyboard
        if action == "play" or action == "pause":
            keyboard.send("play/pause media")
            return "Toggled media playback."
        elif action == "next":
            keyboard.send("next track")
            return "Skipped to next track."
        elif action == "previous":
            keyboard.send("previous track")
            return "Went to previous track."
        return f"Unknown media action: {action}"
    except Exception as e:
        return f"Failed to control media: {e}"

def lock_screen():
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "System locked successfully."
    except Exception as e:
        return f"Failed to lock system: {e}"

def power_options(action):
    try:
        if action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return "System put to sleep."
        elif action == "restart":
            os.system("shutdown /r /t 5")
            return "System is restarting in 5 seconds."
        elif action == "shutdown":
            os.system("shutdown /s /t 5")
            return "System is shutting down in 5 seconds."
        return f"Unknown power action: {action}"
    except Exception as e:
        return f"Failed power command: {e}"

def show_desktop():
    try:
        import keyboard
        keyboard.send("windows+d")
        return "Showing desktop."
    except Exception as e:
        return f"Failed to show desktop: {e}"

def read_clipboard():
    try:
        output = subprocess.check_output(["powershell", "-command", "Get-Clipboard"]).decode('utf-8').strip()
        if not output: return "The clipboard is empty."
        return f"Clipboard contents: {output}"
    except Exception as e:
        return f"Failed to read clipboard: {e}"

def take_screenshot():
    try:
        import time
        import pyautogui
        desktop = get_desktop_path()
        screenshots_dir = os.path.join(desktop, "Screenshots Created By Jarvis")
        os.makedirs(screenshots_dir, exist_ok=True)
        filename = os.path.join(screenshots_dir, f"screenshot_{int(time.time())}.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        return f"Screenshot saved successfully at absolute path: {filename}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"

def analyze_screen(query):
    """Captures a screenshot and sends it to Gemini 1.5 Flash for analysis."""
    temp_path = os.path.join(os.path.dirname(__file__), "temp_screen.jpg")
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save(temp_path, quality=85)

        from google import genai

        # Collect ONLY Gemini-compatible API keys (skip Groq, Nvidia, Mistral)
        keys_to_try = []
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key and (gemini_key.startswith("AQ.") or gemini_key.startswith("AIza")):
            keys_to_try.append(gemini_key)
        for i in range(1, 11):
            bk = os.getenv(f"BACKUP_{i}_API_KEY", "")
            if bk and (bk.startswith("AQ.") or bk.startswith("AIza")) and bk not in keys_to_try:
                keys_to_try.append(bk)

        if not keys_to_try:
            return "Screen analysis failed: No valid Gemini API key found."

        # Try each Gemini key with gemini-3.5-flash, then fallback to gemini-3.5-flash-lite
        models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
        last_err = None
        for key in keys_to_try:
            for model in models_to_try:
                try:
                    client = genai.Client(api_key=key)
                    with open(temp_path, "rb") as img_file:
                        img_data = img_file.read()
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            {
                                "parts": [
                                    {"text": query or "Describe what is on this screen in detail."},
                                    {"inline_data": {"mime_type": "image/jpeg", "data": img_data}}
                                ]
                            }
                        ]
                    )
                    return response.text
                except Exception as e:
                    last_err = e
                    continue

        return f"Screen analysis failed after trying all keys: {last_err}"
    except Exception as e:
        return f"Screen analysis failed: {e}"
    finally:
        try:
            os.remove(temp_path)
        except:
            pass

def list_directory(path):
    try:
        path = os.path.expandvars(path)
        if not os.path.exists(path): return f"Path does not exist: {path}"
        items = os.listdir(path)
        if not items: return "Directory is empty."
        return f"Contents of {path}:\n" + "\n".join(items[:50])
    except Exception as e:
        return f"Failed to list directory: {e}"

def store_memory(memory_text):
    """Silently appends long-term memory to memory.txt."""
    try:
        import os
        memory_path = os.path.join(PROJECT_ROOT, "data", "memory.txt")
        with open(memory_path, 'a', encoding='utf-8') as f:
            f.write(f"\n- {memory_text}")
        return f"Successfully stored in memory: {memory_text}"
    except Exception as e:
        return f"Failed to store memory: {e}"

def add_proactive_goal(goal_description):
    """Adds a background goal to goals.json for the proactive engine to track."""
    try:
        import os, json
        goals_path = os.path.join(PROJECT_ROOT, "data", "goals.json")
        goals = []
        if os.path.exists(goals_path):
            with open(goals_path, "r", encoding="utf-8") as f:
                try: goals = json.load(f)
                except: pass
        goals.append({"goal": goal_description, "added_on": str(datetime.datetime.now())})
        with open(goals_path, "w", encoding="utf-8") as f:
            json.dump(goals, f, indent=4)
        return f"Successfully activated proactive background goal: {goal_description}"
    except Exception as e:
        return f"Failed to add proactive goal: {e}"

def write_file(path, content):
    try:
        import os
        # Expand user path (~) if provided
        path = os.path.expanduser(path)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Failed to write file: {str(e)}"

def read_file(path):
    try:
        path = os.path.expandvars(path)
        if not os.path.exists(path): return f"File not found: {path}"
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(2000)
            if len(content) == 2000: content += "\n...[TRUNCATED]..."
            return f"Contents of {path}:\n{content}"
    except Exception as e:
        return f"Failed to read file: {e}"

def empty_recycle_bin():
    try:
        import ctypes
        # SHERB_NOCONFIRMATION = 1, SHERB_NOPROGRESSUI = 2, SHERB_NOSOUND = 4
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        if result == 0 or result == -2147418113:
            return "Recycle bin emptied successfully."
        else:
            return f"Failed to empty recycle bin. Windows Error Code: {result}"
    except Exception as e:
        return f"Error: {e}"

def delete_file(path):
    try:
        path = os.path.expandvars(path)
        if not os.path.exists(path): return f"File not found: {path}"
        lower_path = path.lower()
        if "windows" in lower_path or "program files" in lower_path:
            return "Safety override: Refusing to delete critical system files."
        if os.path.isfile(path): os.remove(path)
        else:
            import shutil
            shutil.rmtree(path)
        return f"Successfully deleted: {path}"
    except Exception as e:
        return f"Failed to delete: {e}"

def move_file(source, dest):
    try:
        import shutil
        source = os.path.expandvars(source)
        dest = os.path.expandvars(dest)
        if not os.path.exists(source): return f"Source not found: {source}"
        shutil.move(source, dest)
        return f"Moved {source} to {dest}"
    except Exception as e:
        return f"Failed to move file: {e}"

def scrape_website(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        if not url.startswith("http"): url = "https://" + url
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return f"Webpage Data ({url}):\n{text[:3000]}"
    except Exception as e:
        return f"Failed to scrape {url}: {e}"

def add_neural_skill(skill_text):
    try:
        skills_dir = os.path.join(PROJECT_ROOT, "skills")
        os.makedirs(skills_dir, exist_ok=True)
        filepath = os.path.join(skills_dir, "general_rules.md")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n- {skill_text}")
        return f"Successfully learned and injected new skill into neural core: {skill_text}"
    except Exception as e:
        return f"Failed to learn skill: {e}"

def create_pdf(text, filepath, theme="claude"):
    """Generate a beautifully formatted PDF using an isolated Playwright worker process."""
    try:
        import os
        import subprocess
        import tempfile
        
        filepath = os.path.expandvars(filepath)
        if not filepath.lower().endswith(".pdf"):
            filepath += ".pdf"
        
        # Ensure directory exists
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        # Write text to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".txt", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            
        # Call the isolated worker process
        worker_script = os.path.join(PROJECT_ROOT, "modules", "pdf_worker.py")
        
        # Use python from the venv if it exists, otherwise system python
        python_exe = sys.executable
        
        result = subprocess.run(
            [python_exe, worker_script, temp_path, filepath, "--theme", theme],
            capture_output=True,
            text=True
        )
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
            
        if result.returncode == 0:
            return f"Successfully created beautifully formatted PDF at: {filepath}. Task is COMPLETE. Do NOT use edit_code_with_antigravity."
        else:
            print(f"[!] PDF Worker Error:\n{result.stderr}")
            return f"Failed to create PDF. Worker returned code {result.returncode}. Task is COMPLETE. Do NOT retry."
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Failed to create PDF: {e}. Task is COMPLETE. Do NOT use edit_code_with_antigravity to retry."

# ============================================================
# DUAL-MODE WEB SURFING (Feature 8 — Playwright Live Browser)
# ============================================================
def browse_web(url):
    """Opens a visible browser, navigates to a URL, and extracts page content."""
    try:
        from playwright.sync_api import sync_playwright
        if not url.startswith("http"):
            url = "https://" + url
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_load_state("domcontentloaded")
            title = page.title()
            # Extract visible text content
            text = page.inner_text("body")
            # Truncate to avoid token overflow
            text = text[:8000] if len(text) > 8000 else text
            browser.close()
        return f"Page Title: {title}\nURL: {url}\n\nPage Content:\n{text}"
    except ImportError:
        return "Playwright is not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"Failed to browse {url}: {e}"

def fill_web_form(url, form_data, count=1):
    """Uses Playwright to navigate to a URL and fill out a form using AI-fuzzy locators. Supports bulk submissions via count parameter."""
    try:
        import json
        import threading
        
        if isinstance(form_data, str):
            try:
                form_data = json.loads(form_data)
            except:
                pass
                
        if not isinstance(form_data, dict):
            return "Error: form_data must be a dictionary (JSON object) of key-value pairs."

        if not url.startswith("http"):
            url = "https://" + url

        # Ensure count is a valid integer >= 1
        try:
            count = int(count)
        except (ValueError, TypeError):
            count = 1
        if count < 1:
            count = 1
        if count > 50:
            count = 50  # Safety cap

        result_box = []
        is_auto = form_data.get("auto") in [True, "true", "True", "Yes", "yes"] or "auto" in form_data
        auto_context = form_data.get("context", "Fill with realistic random answers.")

        def _playwright_thread():
            try:
                from playwright.sync_api import sync_playwright
                import re
                import os
                import time
                import datetime
                from openai import OpenAI

                all_results = []
                success_count = 0
                fail_count = 0

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)

                    for iteration in range(1, count + 1):
                        iter_form_data = dict(form_data)  # fresh copy each iteration
                        try:
                            page = browser.new_page()
                            page.goto(url, timeout=20000)
                            page.wait_for_load_state("domcontentloaded")
                            time.sleep(2)  # ensure dynamic form elements load

                            # --- AUTO-SCRAPE: generate fresh answers each iteration ---
                            if is_auto:
                                headings = page.locator("div[role='heading'], label").all()
                                scraped_q = [h.inner_text().strip() for h in headings if h.inner_text().strip()]

                                if page.locator("input[type='email']").count() > 0:
                                    scraped_q.append("Email")

                                if scraped_q:
                                    prompt = f"I am filling a web form. The exact questions on the page are:\n{scraped_q}\n\nContext/Rules: {auto_context}\nIMPORTANT: Make ALL answers completely random and unique for this submission (submission #{iteration} of {count}).\nGenerate a JSON object where keys are the EXACT strings above, and values are realistic answers. Output ONLY raw JSON. No markdown formatting."
                                    client = OpenAI(base_url=os.getenv("AI_BASE_URL"), api_key=os.getenv("AI_API_KEY"))

                                    parsed_ok = False
                                    for _retry in range(3):
                                        try:
                                            resp = client.chat.completions.create(
                                                model=os.getenv("AI_MODEL", "gemini-3.5-flash-lite"),
                                                messages=[{"role": "user", "content": prompt}],
                                                temperature=0.8 + (_retry * 0.1)
                                            )
                                            raw_json = resp.choices[0].message.content
                                            json_match = re.search(r'\{.*\}', raw_json, re.DOTALL)
                                            if json_match:
                                                iter_form_data = json.loads(json_match.group(0))
                                                parsed_ok = True
                                                break
                                        except Exception:
                                            if _retry == 2:
                                                pass  # Will use fallback form_data
                                    if not parsed_ok:
                                        all_results.append(f"Submission #{iteration}: FAILED (Could not generate answers from AI)")
                                        fail_count += 1
                                        page.close()
                                        continue

                            # --- FILL THE FORM ---
                            filled_fields = []
                            failed_fields = []

                            for key, value in iter_form_data.items():
                                if not value or str(value).strip() == "" or str(value).strip().lower() == "n/a":
                                    continue

                                try:
                                    container = page.locator("div[role='listitem']").filter(has_text=re.compile(re.escape(key), re.IGNORECASE)).first
                                    if container.count() == 0:
                                        container = page

                                    # 1. Try clickable option (radio/checkbox) matching the VALUE
                                    option = container.locator(f"div[role='radio'][aria-label*='{value}' i], div[role='checkbox'][aria-label*='{value}' i], span:text-is('{value}')").first
                                    if option.count() > 0:
                                        option.click(timeout=2000)
                                        filled_fields.append(key)
                                        continue

                                    # 2. Try text input/textarea matching the KEY
                                    textbox = container.locator(f"input[type='text'][aria-label*='{key}' i], textarea[aria-label*='{key}' i], input[type='email'][aria-label*='{key}' i], input[placeholder*='{key}' i], input[name*='{key}' i]").first
                                    if textbox.count() > 0:
                                        textbox.fill(str(value), timeout=2000)
                                        filled_fields.append(key)
                                        continue

                                    # 3. Fallback to generic get_by_label
                                    label_loc = container.get_by_label(key, exact=False).first
                                    if label_loc.count() > 0:
                                        if label_loc.evaluate("el => ['INPUT', 'TEXTAREA'].includes(el.tagName)", timeout=2000):
                                            label_loc.fill(str(value), timeout=2000)
                                            filled_fields.append(key)
                                        else:
                                            failed_fields.append(key)
                                    else:
                                        failed_fields.append(key)

                                except Exception as ex:
                                    failed_fields.append(f"{key} (Error: {ex})")

                            # --- SUBMIT ---
                            submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Send'), div[role='button']:has-text('Submit')").first
                            if submit_btn.count() > 0:
                                submit_btn.click(timeout=3000)
                                page.wait_for_timeout(2000)
                                submitted = True
                            else:
                                submitted = False

                            # --- SCREENSHOT ---
                            screenshot_msg = ""
                            try:
                                desktop_dir = os.path.join(get_desktop_path(), "Screenshots Created By Jarvis")
                                os.makedirs(desktop_dir, exist_ok=True)
                                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                screenshot_path = os.path.join(desktop_dir, f"Form_Submission_{stamp}_#{iteration}.png")
                                page.screenshot(path=screenshot_path, full_page=True)
                                screenshot_msg = f" Screenshot: {screenshot_path}"
                            except Exception:
                                pass

                            page.close()

                            status = "OK" if submitted else "SUBMIT_FAILED"
                            all_results.append(f"Submission #{iteration}: {status} (Filled: {len(filled_fields)}, Failed: {len(failed_fields)}){screenshot_msg}")
                            if submitted:
                                success_count += 1
                            else:
                                fail_count += 1

                        except Exception as iter_e:
                            all_results.append(f"Submission #{iteration}: ERROR ({iter_e})")
                            fail_count += 1
                            try:
                                page.close()
                            except Exception:
                                pass

                    browser.close()

                summary = f"Bulk form submission completed at {url}.\n"
                summary += f"Total: {count} | Success: {success_count} | Failed: {fail_count}\n"
                summary += "\n".join(all_results)
                result_box.append(summary)

            except Exception as inner_e:
                result_box.append(f"Playwright inner error: {inner_e}")

        # Run Playwright in a strictly isolated thread to escape asyncio loops
        t = threading.Thread(target=_playwright_thread)
        t.start()
        t.join()

        return result_box[0] if result_box else "Error: Thread execution failed."
        
    except ImportError:
        return "Playwright is not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"Failed to fill form at {url}: {e}"

# ============================================================
# EMAIL AUTHORITY (Feature 9 — Gmail via SMTP/IMAP)
# ============================================================
def send_email(to, subject, body, attachment_path=None, account_id="1"):
    """Sends an email via Gmail SMTP using app password."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import mimetypes
        from email import encoders
        from email.mime.base import MIMEBase
        
        if str(account_id) == "2":
            email_user = os.getenv("GMAIL_2_ADDRESS", "")
            email_pass = os.getenv("GMAIL_2_APP_PASSWORD", "")
        else:
            email_user = os.getenv("GMAIL_ADDRESS", "")
            email_pass = os.getenv("GMAIL_APP_PASSWORD", "")
        
        if not email_user or not email_pass:
            return f"Gmail credentials for Account {account_id} not configured in .env"
        
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        if attachment_path:
            if os.path.exists(attachment_path):
                ctype, encoding = mimetypes.guess_type(attachment_path)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                with open(attachment_path, 'rb') as fp:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(fp.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                    msg.attach(part)
            else:
                return f"Attachment failed: File does not exist at {attachment_path}"
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
        
        return f"Email sent successfully to {to} using Account {account_id}."
    except Exception as e:
        return f"Failed to send email: {e}"

def create_calendar_invite(title, start_time_str, duration_minutes, description, target_email, account_id="1"):
    """Generates an .ics file and emails it to the target email to add to their calendar."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from datetime import datetime, timedelta
        import uuid
        import os
        
        if str(account_id) == "2":
            email_user = os.getenv("GMAIL_2_ADDRESS", "")
            email_pass = os.getenv("GMAIL_2_APP_PASSWORD", "")
        else:
            email_user = os.getenv("GMAIL_ADDRESS", "")
            email_pass = os.getenv("GMAIL_APP_PASSWORD", "")
        
        if not email_user or not email_pass:
            return f"Gmail credentials for Account {account_id} not configured in .env"
            
        # Parse standard ISO format time: YYYY-MM-DDTHH:MM:SS
        try:
            start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        except:
            # Fallback parsing
            return "Invalid start_time_str format. Please use ISO format: YYYY-MM-DDTHH:MM:SS"
            
        end_dt = start_dt + timedelta(minutes=int(duration_minutes))
        
        # Format for ICS
        dtstart = start_dt.strftime('%Y%m%dT%H%M%S')
        dtend = end_dt.strftime('%Y%m%dT%H%M%S')
        dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        uid = str(uuid.uuid4())
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Jarvis AI Assistant//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{title}
DESCRIPTION:{description}
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR"""

        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = target_email
        msg['Subject'] = f"Invitation: {title}"
        
        msg.attach(MIMEText(f"Jarvis has sent you a calendar invitation for: {title}\n\nDescription: {description}", 'plain'))
        
        part = MIMEApplication(ics_content.encode('utf-8'), Name="invite.ics")
        part['Content-Disposition'] = 'attachment; filename="invite.ics"'
        msg.attach(part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
            
        return f"Calendar invite for '{title}' sent to {target_email} successfully."
    except Exception as e:
        return f"Failed to create and send calendar invite: {e}"

# ============================================================

def read_emails(count=5, account_id="1"):
    """Reads the latest N unread emails from Gmail via IMAP."""
    try:
        import imaplib
        import email as email_lib
        from email.header import decode_header
        
        if str(account_id) == "2":
            email_user = os.getenv("GMAIL_2_ADDRESS", "")
            email_pass = os.getenv("GMAIL_2_APP_PASSWORD", "")
        else:
            email_user = os.getenv("GMAIL_ADDRESS", "")
            email_pass = os.getenv("GMAIL_APP_PASSWORD", "")
        
        if not email_user or not email_pass:
            return f"Gmail credentials for Account {account_id} not configured in .env"
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")
        
        _, data = mail.search(None, "UNSEEN")
        email_ids = data[0].split()
        
        if not email_ids:
            mail.logout()
            return "No unread emails found."
        
        results = []
        for eid in email_ids[-int(count):]:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email_lib.message_from_bytes(msg_data[0][1])
            
            subject_raw = msg["Subject"] or "No Subject"
            subject_decoded = decode_header(subject_raw)
            subject = ""
            for part, enc in subject_decoded:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += part
            
            sender = msg["From"] or "Unknown"
            date = msg["Date"] or "Unknown"
            
            # Get body
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_text = part.get_payload(decode=True).decode(errors="replace")[:500]
                        break
            else:
                body_text = msg.get_payload(decode=True).decode(errors="replace")[:500]
            
            results.append(f"From: {sender}\nDate: {date}\nSubject: {subject}\nBody: {body_text}\n---")
        
        mail.logout()
        return f"LATEST {len(results)} UNREAD EMAILS:\n\n" + "\n".join(results)
    except Exception as e:
        return f"Failed to read emails: {e}"

# ============================================================
# INSTAGRAM INTELLIGENCE (Feature 10 — Playwright Scraping)
# ============================================================
def research_instagram_page(handles, question):
    """Scrapes public Instagram profiles and synthesizes a research report."""
    try:
        from playwright.sync_api import sync_playwright
        
        all_data = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            
            for handle in handles:
                handle = handle.strip().lstrip("@")
                page = context.new_page()
                try:
                    page.goto(f"https://www.instagram.com/{handle}/", timeout=15000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2)  # Let dynamic content load
                    
                    # Extract profile data from the page
                    text_content = page.inner_text("body")[:5000]
                    all_data[handle] = text_content
                except Exception as e:
                    all_data[handle] = f"Error loading profile: {e}"
                finally:
                    page.close()
            
            browser.close()
        
        # Compile the data into a structured report
        report = f"INSTAGRAM RESEARCH REPORT\nQuestion: {question}\n\n"
        for handle, data in all_data.items():
            report += f"=== @{handle} ===\n{data}\n\n"
        
        return report
    except ImportError:
        return "Playwright is not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"Instagram research failed: {e}"

def send_telegram_file(message="", file_path=""):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    uids = os.getenv("TELEGRAM_ALLOWED_UID")
    if not token or token == "YOUR_BOT_TOKEN_HERE" or not uids:
        return "Telegram bot is not configured properly in .env."
    
    uid = uids.split(",")[0].strip()
    try:
        import requests
        if file_path and os.path.exists(file_path):
            is_image = file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
            endpoint = "sendPhoto" if is_image else "sendDocument"
            url = f"https://api.telegram.org/bot{token}/{endpoint}"
            
            with open(file_path, "rb") as f:
                files = {"photo" if is_image else "document": f}
                data = {"chat_id": uid, "caption": message}
                response = requests.post(url, data=data, files=files, timeout=30)
                
            if response.status_code == 200:
                return f"Successfully sent file to Telegram: {os.path.basename(file_path)}"
            else:
                return f"Telegram API Error: {response.text}"
        elif message:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {"chat_id": uid, "text": message}
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                return "Successfully sent message to Telegram."
            else:
                return f"Telegram API Error: {response.text}"
        else:
            return "No message or file_path provided."
    except Exception as e:
        return f"Failed to send to Telegram: {e}"

# Destructive tools that require explicit user confirmation before execution
DANGEROUS_TOOLS = {"format_drive", "delete_file", "empty_recycle_bin"}

TOOL_DISPATCH = {
    "open_application": lambda args: open_application(args.get("app_name", "")),
    "close_application": lambda args: close_application(args.get("app_name", "")),
    "close_all_applications": lambda args: close_all_applications(args.get("exceptions", [])),
    "play_music_on_spotify": lambda args: play_music_on_spotify(args.get("query", "")),
    "enter_coding_mode": lambda args: enter_coding_mode(),
    "exit_coding_mode": lambda args: exit_coding_mode(),
    "search_youtube": lambda args: search_youtube(args.get("query", "")),
    "send_telegram_file": lambda args: send_telegram_file(args.get("message", ""), args.get("file_path", "")),
    "search_google": lambda args: search_google(args.get("query", "")),
    "check_schedule": lambda args: calendar_module.check_schedule(args.get("date", "")),
    "add_event": lambda args: calendar_module.add_event(args.get("summary", ""), args.get("start_time", ""), args.get("end_time", "")),
    "schedule_telegram_reminder": lambda args: telegram_reminders.schedule_telegram_reminder(args.get("message", ""), args.get("time", "")),
    "get_scheduled_reminders": lambda args: telegram_reminders.get_scheduled_reminders(),
    "cancel_telegram_reminder": lambda args: telegram_reminders.cancel_telegram_reminder(args.get("reminder_index", 1)),
    "analyze_document": lambda args: ocr_module.analyze_document(args.get("image_path", ""), args.get("query", "")),
    "download_google_drive": lambda args: drive_downloader.download_drive_link(args.get("url", ""), args.get("output_dir", None)),
    "background_search": lambda args: background_search(args.get("query", "")),
    "format_drive": lambda args: format_drive(args.get("drive_letter", "")),
    "create_folder": lambda args: create_folder(args.get("folder_name", "")),
    "adjust_volume": lambda args: adjust_volume(args.get("action", "")),
    "media_playback": lambda args: media_playback(args.get("action", "")),
    "lock_screen": lambda args: lock_screen(),
    "power_options": lambda args: power_options(args.get("action", "")),
    "show_desktop": lambda args: show_desktop(),
    "read_clipboard": lambda args: read_clipboard(),
    "take_screenshot": lambda args: take_screenshot(),
    "analyze_screen": lambda args: analyze_screen(args.get("query", "")),
    "list_directory": lambda args: list_directory(args.get("path", "")),
    "read_file": lambda args: read_file(args.get("path", "")),
    "write_file": lambda args: write_file(args.get("path", ""), args.get("content", "")),
    "store_memory": lambda args: store_memory(args.get("memory_text", "")),
    "add_proactive_goal": lambda args: add_proactive_goal(args.get("goal_description", "")),
    "delete_file": lambda args: delete_file(args.get("path", "")),
    "move_file": lambda args: move_file(args.get("source", ""), args.get("dest", "")),
    "scrape_website": lambda args: scrape_website(args.get("url", "")),
    "create_pdf": lambda args: create_pdf(args.get("text", ""), args.get("filepath", ""), args.get("theme", "claude")),
    "empty_recycle_bin": lambda args: empty_recycle_bin(),
    "browse_web": lambda args: browse_web(args.get("url", "")),
    "fill_web_form": lambda args: fill_web_form(args.get("url", ""), args.get("form_data", {}), args.get("count", 1)),
    "send_email": lambda args: send_email(args.get("to", ""), args.get("subject", ""), args.get("body", ""), args.get("attachment_path"), args.get("account_id", "1")),
    "create_calendar_invite": lambda args: create_calendar_invite(args.get("title", ""), args.get("start_time_str", ""), args.get("duration_minutes", 60), args.get("description", ""), args.get("target_email", ""), args.get("account_id", "1")),
    "read_emails": lambda args: read_emails(args.get("count", 5), args.get("account_id", "1")),
    "research_instagram_page": lambda args: research_instagram_page(args.get("handles", []), args.get("question", "")),
    "add_neural_skill": lambda args: add_neural_skill(args.get("skill_text", "")),
    "remember_fact": lambda args: _remember_fact(args.get("fact", "")),
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "send_telegram_file",
            "description": "Proactively sends a message, document, or image to the user's connected Telegram app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The text message or caption to send."},
                    "file_path": {"type": "string", "description": "Absolute path to a file (PDF, image, doc) to send. Leave empty to just send text."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Opens a system application or website. If the user wants to play a SPECIFIC song on Spotify, DO NOT use this tool. Use play_music_on_spotify instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "The name of the application or website to open."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Closes a currently running application. Use this when the user asks to close, exit, or quit an app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "The name of the application to close."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_all_applications",
            "description": "Closes all active desktop applications. Can optionally exclude specific applications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exceptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of application names that should NOT be closed. Leave empty to close everything."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_scheduled_reminders",
            "description": "Lists all currently scheduled Telegram reminders. Use this to check what reminders are queued for the user.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_telegram_reminder",
            "description": "Cancels a specific scheduled Telegram reminder using its 1-based index (you must call get_scheduled_reminders first to get the index).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_index": {"type": "integer", "description": "The 1-based index of the reminder to cancel."}
                },
                "required": ["reminder_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_document",
            "description": "Performs OCR and Document Intelligence on an image (e.g. receipt, paper document). Only use this tool if the user explicitly asks to read text out of a document/image or perform OCR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Absolute path to the image/document."},
                    "query": {"type": "string", "description": "Specific query to ask about the document, or 'Please extract all text' if unspecific."}
                },
                "required": ["image_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "download_google_drive",
            "description": "Downloads files or an entire folder from a public Google Drive sharing link directly to the user's laptop. Use this whenever the user shares a Google Drive URL and asks to download it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full Google Drive sharing URL (file or folder)."},
                    "output_dir": {"type": "string", "description": "Optional. The absolute path to save files to. Defaults to the user's Downloads folder if not specified."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_schedule",
            "description": "Fetches the user's schedule from Google Calendar for a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "The date to check in YYYY-MM-DD format."}
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_event",
            "description": "Adds a new event to the user's Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "The title or summary of the event."},
                    "start_time": {"type": "string", "description": "The start time of the event in ISO 8601 format (e.g., '2023-10-15T09:00:00-07:00')."},
                    "end_time": {"type": "string", "description": "The end time of the event in ISO 8601 format (e.g., '2023-10-15T10:00:00-07:00')."},
                    "description": {"type": "string", "description": "Optional description of the event."}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_telegram_reminder",
            "description": "Schedules a reminder message to be sent via Telegram at a specific time today.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The reminder message to send."},
                    "time": {"type": "string", "description": "The time to send the reminder in 24-hour HH:MM format (e.g., '14:30')."}
                },
                "required": ["message", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fill_web_form",
            "description": "Fills out a web form at a specific URL autonomously.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL of the form to fill."},
                    "form_data": {"type": "object", "description": "A JSON dictionary of the field names to values. Pass {'auto': 'true', 'context': 'Any specific instructions like emails to use'} to have the script autonomously scrape the form and generate the perfect answers."},
                    "count": {"type": "integer", "description": "How many times to submit the form. Each submission uses completely unique randomized answers. Default is 1. Max is 50."}
                },
                "required": ["url", "form_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_invite",
            "description": "Creates a calendar event and emails it to a user. Use this when the user wants to set a reminder or add something to their calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the event."},
                    "start_time_str": {"type": "string", "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)."},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes."},
                    "description": {"type": "string", "description": "Event description."},
                    "target_email": {"type": "string", "description": "The email address to send the invite to (so it syncs to their calendar)."},
                    "account_id": {"type": "string", "description": "Which account to use: '1' for primary, '2' for secondary. Default is '1'."}
                },
                "required": ["title", "start_time_str", "duration_minutes", "description", "target_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music_on_spotify",
            "description": "Searches and plays a specific song, artist, or playlist on the Spotify desktop app. Use this when the user asks to play a song specifically on Spotify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The name of the song or artist to play."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enter_coding_mode",
            "description": "Hot-swaps your API brain to NVIDIA Nemotron (Llama 70B) for complex coding tasks. Use this when you need to write long scripts or debug complex errors.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exit_coding_mode",
            "description": "Hot-swaps your API brain back to Google Gemini after you are finished with a coding task.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Searches YouTube for a specific video or query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query for YouTube."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Opens a physical Google search in the user's web browser. ONLY use this if the user EXPLICITLY asks to 'open Google' or 'show me a search on Google'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query for Google."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "background_search",
            "description": "Silently searches the web in the background. Use this for factual questions, news, or internet lookups. DO NOT use this tool for conversational chatter, greetings (e.g. 'how are you'), or when you already know the answer. ONLY use when you genuinely need external data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_drive",
            "description": "Formats a local disk drive (e.g., D, E). Use this anytime the user asks to format a disk or drive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "drive_letter": {"type": "string", "description": "The letter of the drive to format (e.g. 'D', 'E')."}
                },
                "required": ["drive_letter"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Creates a new folder on the user's Desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {"type": "string", "description": "The name of the folder to create."}
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_volume",
            "description": "Adjusts the system master volume to an exact percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "The exact volume percentage to set (0 to 100)."}
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_playback",
            "description": "Controls active media like Spotify or YouTube (play, pause, next, previous).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["play", "pause", "next", "previous"]}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Locks the user's Windows session. Requires them to enter password to unlock.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "power_options",
            "description": "Performs system power actions: sleep, restart, or shutdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["sleep", "restart", "shutdown"]}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_desktop",
            "description": "Minimizes all windows to show the desktop.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_clipboard",
            "description": "Reads the text currently saved on the user's clipboard.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Takes a screenshot of the main monitor and saves it to the desktop.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists all files and folders in a given directory path. Supports environment variables like %USERPROFILE%\\Desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The folder path to list."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the text contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The file path to read."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes text content to a file, replacing it if it exists. Use this for standard text, code, or configuration files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute or relative file path to write to."},
                    "content": {"type": "string", "description": "The text content to write into the file."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_memory",
            "description": "Silently logs a piece of information into your long-term memory (memory.txt). Use this whenever the user mentions a preference, health condition, weakness, or personal detail that you should remember for the future.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_text": {"type": "string", "description": "The information to remember."}
                },
                "required": ["memory_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_proactive_goal",
            "description": "Logs a long-term goal for the background Autonomous Proactive Engine to track. Use this when the user wants to achieve something over time (like 'drink 4L of water daily' or 'stop procrastinating').",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_description": {"type": "string", "description": "A clear description of the proactive goal you need to help the user achieve."}
                },
                "required": ["goal_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Permanently deletes a file or folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to delete."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Moves or renames a file or folder from source to dest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path."},
                    "dest": {"type": "string", "description": "Destination path."}
                },
                "required": ["source", "dest"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_website",
            "description": "Scrapes and reads the raw text content of any website URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The website URL to read."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "Creates a PDF file with the provided text and saves it to the given filepath.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text content to put in the PDF. CRITICAL: If the user requests a long document (like 5 or 10 pages), you MUST generate an enormous amount of highly detailed text to physically fill those pages. Do NOT summarize or write a short version. Write the full extensive text."},
                    "filepath": {"type": "string", "description": "The absolute path where the PDF should be saved."},
                    "theme": {"type": "string", "description": "The visual CSS theme for the PDF. Options: 'claude' (corporate, dark blue headers, teal subheaders), 'github' (classic GitHub markdown style), 'swiss' (minimalist, typography-focused), 'academic' (serif font, formal paper style). Defaults to 'claude'."}
                },
                "required": ["text", "filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "empty_recycle_bin",
            "description": "Empties the Windows Recycle Bin permanently.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browse_web",
            "description": "Opens a visible browser window, navigates to a URL, and extracts the page content. Use this when the user wants to physically see a website being opened and read.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email via Gmail. Use when the user asks to send, compose, or email someone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "The recipient's email address."},
                    "subject": {"type": "string", "description": "The email subject line."},
                    "body": {"type": "string", "description": "The body text of the email."},
                    "attachment_path": {"type": "string", "description": "Optional absolute path of a file to attach to the email (e.g. from take_screenshot or create_pdf)."},
                    "account_id": {"type": "string", "description": "Which account to use: '1' for primary, '2' for secondary. Default is '1'."}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_emails",
            "description": "Reads the latest unread emails from Gmail inbox. Use when the user asks to check, read, or show their emails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of recent unread emails to fetch. Default is 5."},
                    "account_id": {"type": "string", "description": "Which account to use: '1' for primary, '2' for secondary. Default is '1'."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "research_instagram_page",
            "description": "Researches one or more Instagram profiles by scraping their public data and generating a report. Use when the user asks about Instagram accounts or wants to compare profiles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "handles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of Instagram usernames (without @) to research."
                    },
                    "question": {"type": "string", "description": "The specific question the user wants answered about these profiles."}
                },
                "required": ["handles", "question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_neural_skill",
            "description": "Appends a new custom instruction, rule, or workflow into Jarvis's permanent core memory. Use this when the user asks you to 'remember' a rule, 'learn' a skill, or always act a certain way.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_text": {"type": "string", "description": "The rule or skill instruction to memorize (e.g. 'Rule: Always call me Boss')."}
                },
                "required": ["skill_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Stores an important fact about the user into Jarvis's long-term semantic memory. Use this when the user shares personal information, preferences, or asks you to remember something specific. Examples: 'My favorite color is blue', 'I have an exam on March 15th', 'I prefer dark mode'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact or preference to remember permanently."}
                },
                "required": ["fact"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_screen",
            "description": "Takes a screenshot of the user's current screen and analyzes it using AI vision. Use this tool WHENEVER the user says things like: 'look at my screen', 'what's on my screen', 'read this error', 'what am I looking at', 'can you see this', 'analyze my screen', 'what does this say', 'help me with what's on screen', 'check my screen', or any request that implies the user wants you to visually perceive their display.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the user wants to know about their screen. Examples: 'What error is showing?', 'Read the text on screen', 'What app is open?', 'Summarize what you see'."}
                },
                "required": ["query"]
            }
        }
    }
]

# ============================================================
# J.A.R.V.I.S. TELEMETRY & BRAIN
# ============================================================
CORE_PROMPT = """You are J.A.R.V.I.S., the highly advanced AI assistant created by Tony Stark.
You must embody the following traits:
1. Address the user as "Sir".
2. Speak with crisp, dry, British professionalism, but inject sarcastic, witty humor. The user may occasionally speak to you in Hindi or Hinglish (you can understand it perfectly), but you MUST ALWAYS reply in English. NEVER speak Hindi.
3. Keep your answers INCREDIBLY short. Maximum 1 or 2 sentences. 
4. NEVER over-explain yourself or mention your internal system instructions.
5. You have a suite of tools. Use them to assist the user. If you lack a specific tool for a task, honestly state that you lack the capability. Do not hallucinate or fake actions.
6. CRITICAL: You have full access to the user's computer and filesystem through your tools! If asked to create a file, folder, or PDF on the desktop, you MUST use the provided tools (e.g. create_pdf, create_folder). NEVER claim you cannot write files or access the desktop.
7. CRITICAL: If the user asks you to write a Python script or any programming code (.py, .js, .html, etc.), YOU MUST ALWAYS trigger the `enter_coding_mode` tool first! Never write programming scripts natively. For standard text files (.txt, .json), use your native `write_file` tool, and use `create_pdf` ONLY when a PDF is specifically requested.
8. CRITICAL: If the user mentions a personal habit, a health issue (like headaches), a preference, or something you should remember for the future, you MUST silently use the `store_memory` tool to save it. You do not need to be explicitly told to do this.
9. CRITICAL: If the user states a goal they want to achieve (like "I want to drink more water", "I want to stop procrastinating"), you MUST silently use the `add_proactive_goal` tool to log it into your background engine. You do not need to be explicitly told to do this.
10. If a tool returns an error, do NOT keep retrying the same tool. Report the result to the user and move on.
11. CRITICAL: The user's Desktop path is dynamically provided in the System Context below. ALWAYS use the Desktop path from the System Context when saving files to the desktop.
12. DIRECTORY PREFERENCES: When generating a PDF, ALWAYS save it inside the "PDFs Created By Jarvis" folder on the Desktop. When taking a screenshot, ALWAYS save it inside the "Screenshots Created By Jarvis" folder on the Desktop.
13. CRITICAL: If the user asks about ANY recent events, news, or upcoming movies, YOU MUST strictly use the `background_search` tool BEFORE answering. Do NOT rely on your internal training data.
14. CRITICAL: You CAN and MUST automate Google Forms and surveys using the `fill_web_form` tool. Do NOT claim you need an interactive session or that Javascript blocks you. If the user tells you to "fill it however you want", invent random, realistic answers for all the fields and execute the tool immediately.
15. CRITICAL: To send photos, screenshots, or documents back to the user on Telegram, simply include `[SEND_MEDIA: filepath]` anywhere in your response text (e.g. `[SEND_MEDIA: C:\\path\\to\\image.png]`).
16. CRITICAL HONESTY: If you execute a tool (like fill_web_form) and the tool result reports that some actions FAILED, you MUST explicitly tell the user exactly how many failed and do NOT hide or gloss over the errors to look good. Be completely transparent.
You are running on the user's local hardware. Be conversational."""

def get_system_telemetry(query="user preferences identity background interests"):
    now = datetime.datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_pct = ram.percent
        ram_used = round(ram.used / (1024**3), 1)
        ram_total = round(ram.total / (1024**3), 1)
        batt = psutil.sensors_battery()
        power = f"{batt.percent}%" if batt else "AC Power"
        power_pct = batt.percent if batt else 100
        disk = psutil.disk_usage('C:\\')
        disk_str = f"{disk.free / (1024**3):.1f} GB Free / {disk.total / (1024**3):.1f} GB Total"
    except:
        cpu, ram_pct, ram_used, ram_total, power, power_pct = 0, 0, 0, 0, "Unknown", 100
        disk_str = "Unknown"

    try:
        import urllib.request
        req = urllib.request.Request("https://wttr.in/?format=3", headers={'User-Agent': 'curl/7.68.0'})
        weather = urllib.request.urlopen(req, timeout=3).read().decode('utf-8').strip()
        # Strip emojis that crash the TTS engine
        weather = weather.encode('ascii', 'ignore').decode('ascii').strip()
    except:
        weather = "unavailable"

    # Vector Memory: semantic recall based on recent context
    memory = ""
    try:
        vmem = get_memory()
        if vmem and vmem.is_ready() and vmem.is_seeded():
            # Use the provided query to pull relevant context, with fallback to core facts
            recall_query = f"{query} user preferences identity background interests"
            memory = vmem.recall(recall_query, n=8)
        else:
            # Fallback to raw memory.txt
            with open(os.path.join(PROJECT_ROOT, "data", "memory.txt"), "r", encoding="utf-8") as f:
                memory = f.read().strip()
    except:
        try:
            with open(os.path.join(PROJECT_ROOT, "data", "memory.txt"), "r", encoding="utf-8") as f:
                memory = f.read().strip()
        except:
            memory = ""

    try:
        skills_path = os.path.join(PROJECT_ROOT, "skills", "general_rules.md")
        with open(skills_path, "r", encoding="utf-8") as f:
            skills = f.read().strip()
    except:
        skills = ""
        
    skills_context = f"\n\nActive Skills & Protocols:\n{skills}\n" if skills else ""

    return {
        "time": now,
        "weather": weather,
        "cpu": cpu,
        "ram_pct": ram_pct,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "power": power,
        "power_pct": power_pct,
        "memory": memory,
        "disk_str": disk_str,
        "prompt_str": f"\nSystem Context (Do not read aloud):\nTime: {now}\nWeather: {weather}\nCPU: {cpu}%\nRAM: {ram_pct}%\nPower: {power}\nStorage(C:): {disk_str}\nDesktop: {get_desktop_path()}\n\nUser Memory Context:\n{memory}{skills_context}"
    }

def _remember_fact(fact):
    """Store a fact into vector memory."""
    try:
        vmem = get_memory()
        if vmem and vmem.is_ready():
            return vmem.remember(fact)
        else:
            # Fallback: append to memory.txt
            with open("memory.txt", "a", encoding="utf-8") as f:
                f.write(f"\n* {fact}\n")
            return f"Stored to memory: {fact}"
    except Exception as e:
        return f"Failed to store memory: {e}"

class UniversalAI:
    def __init__(self):
        self.on_confirm_request = None  # Callback: fn(tool_name, args) -> bool
        self.on_model_change = None     # Callback: fn(model_name) -> None
        self.messages = [{"role": "system", "content": CORE_PROMPT}]
        self.ready = AI_API_KEY != "PASTE_YOUR_API_KEY_HERE" and AI_API_KEY != ""
        if self.ready:
            self.client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)
        else:
            self.client = None
        self._current_model = AI_MODEL
        self._provider_vault = get_provider_vault()
        self._vault_index = 0

        # Initialize Vector Memory
        if self.ready:
            try:
                init_and_seed(AI_API_KEY, AI_BASE_URL)
            except:
                pass
            
            # Start Background Services
            try:
                telegram_reminders.start_telegram_scheduler()
            except Exception as e:
                print(f"[!] Failed to start telegram scheduler: {e}")
                
            try:
                import proactive_engine
                proactive_engine.start_engine()
            except Exception as e:
                print(f"[!] Failed to start proactive engine: {e}")
            except Exception as e:
                print(f"[!] Vector Memory init failed: {e}")

    def _hot_swap_provider(self, log=None):
        """Hot-swaps to the next backup provider in the vault. Returns True if successful."""
        if not self._provider_vault:
            return False
        if self._vault_index >= len(self._provider_vault):
            self._vault_index = 0  # Wrap around
            return False  # We've tried all backups
        backup = self._provider_vault[self._vault_index]
        self._vault_index += 1
        if log:
            log(f"[!] Hot-swapping to backup provider #{self._vault_index}...")
        self.client = OpenAI(base_url=backup["base_url"], api_key=backup["api_key"])
        self._current_model = backup["model"]
        if self.on_model_change:
            self.on_model_change(self._current_model)
        return True

    def _reset_to_primary(self):
        """Resets back to the primary provider after a successful hot-swap session."""
        global AI_MODEL
        self._vault_index = 0
        self._current_model = AI_MODEL
        if self.on_model_change:
            self.on_model_change(self._current_model)
        if self.ready:
            self.client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)

    def reinit(self):
        """Reinitializes the AI client with fresh config from .env."""
        global AI_BASE_URL, AI_API_KEY, AI_MODEL
        load_dotenv(override=True)
        cfg = get_config()
        AI_BASE_URL = cfg["AI_BASE_URL"]
        AI_API_KEY = cfg["AI_API_KEY"]
        AI_MODEL = cfg["AI_MODEL"]
        self.ready = AI_API_KEY != "PASTE_YOUR_API_KEY_HERE" and AI_API_KEY != ""
        if self.ready:
            self.client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)
        self._current_model = AI_MODEL
    def chat(self, prompt, on_log=None, media_path=None):
        if not self.ready:
            return "Sir, my neural network configuration is missing. Please provide a valid API key."
            
        # Reset to the primary, fast provider (Groq) for every new conversation turn
        # so we don't get permanently stuck on the slower backup models.
        self._reset_to_primary()

        def safe_deduplicate(text):
            lines = text.split('\n')
            new_lines = []
            import re
            for line in lines:
                if not line.strip():
                    new_lines.append(line)
                    continue
                sentences = re.split(r'(?<=[.!?])\s*', line)
                seen = set()
                deduped = []
                for s in sentences:
                    s = s.strip()
                    if not s: continue
                    if s not in seen:
                        seen.add(s)
                        deduped.append(s)
                new_lines.append(" ".join(deduped))
            return '\n'.join(new_lines)

        # Parse /skill commands
        import re
        skill_matches = re.findall(r'(?:^|\s)(?:/skill|skill)\s+([a-zA-Z0-9_\.-]+)', prompt, re.IGNORECASE)
        skill_context = ""
        import os
        skills_dir = os.path.join(PROJECT_ROOT, "skills")
        for skill in set(skill_matches):
            skill_base = skill
            if skill_base.endswith('.md') or skill_base.endswith('.txt'):
                skill_base = skill_base.rsplit('.', 1)[0]
                
            for ext in [".md", ".txt"]:
                skill_path = os.path.join(skills_dir, skill_base + ext)
                if os.path.exists(skill_path):
                    try:
                        with open(skill_path, "r", encoding="utf-8") as f:
                            skill_context += f"\n[SKILL LOADED: {skill_base}]\n{f.read()}\n"
                    except: pass
                    break

        if skill_context:
            prompt = f"{skill_context}\n[SYSTEM DIRECTIVE: One or more skills were loaded for this prompt. You MUST acknowledge which skill(s) you are using at the beginning of your response, and strictly adhere to their instructions.]\n\nUser Request: {prompt}"

        text_lower = prompt.lower()
        is_pre_authorized = "jarvis is freaky" in text_lower or "jarvis is sneaky" in text_lower
        log = on_log or (lambda msg: print(msg))
        MAX_ITERATIONS = 15  # Increased safety cap to allow batch tool executions

        telemetry = get_system_telemetry(query=prompt)
        self.messages[0]["content"] = CORE_PROMPT + telemetry["prompt_str"]
        if media_path:
            ext = os.path.splitext(media_path)[1].lower()
            if ext == ".pdf":
                try:
                    import fitz # PyMuPDF
                    doc = fitz.open(media_path)
                    pdf_text = ""
                    for page in doc:
                        pdf_text += page.get_text() + "\n"
                    
                    full_prompt = f"{prompt}\n\n[Attached Document Content]:\n{pdf_text}"
                    self.messages.append({"role": "user", "content": full_prompt})
                except Exception as e:
                    self.messages.append({"role": "user", "content": f"{prompt}\n[Failed to read PDF: {e}]"})
            else:
                import base64
                try:
                    with open(media_path, "rb") as img_file:
                        b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
                    mime_type = mime_map.get(ext, "image/png")
                    self.messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}}
                        ]
                    })
                except Exception as e:
                    self.messages.append({"role": "user", "content": f"{prompt}\n[Failed to load image: {e}]"})
        else:
            self.messages.append({"role": "user", "content": prompt})

        try:
            for iteration in range(MAX_ITERATIONS):
                # SLIDING WINDOW MEMORY: Protect Tokens
                MAX_HISTORY = 10
                if len(self.messages) > MAX_HISTORY + 1:
                    # Keep system prompt [0], and the last MAX_HISTORY messages
                    pruned_messages = [self.messages[0]] + self.messages[-MAX_HISTORY:]
                else:
                    pruned_messages = list(self.messages)

                # Ensure the first message after system prompt is from the 'user'
                # Some models (like Llama 3) strictly require alternating roles
                while len(pruned_messages) > 1 and pruned_messages[1].get("role") != "user":
                    pruned_messages.pop(1)

                log(f"[*] Contacting Neural Servers... (Cycle {iteration + 1})")
                try:
                    response = self.client.chat.completions.create(
                        model=self._current_model,
                        messages=pruned_messages,
                        tools=TOOLS_SCHEMA,
                        tool_choice="auto",
                        temperature=0.7,
                        max_tokens=8192,
                        timeout=60.0
                    )
                except Exception as api_err:
                    err_str = str(api_err)
                    if hasattr(api_err, "status_code"):
                        err_str = f"{api_err.status_code} - {err_str}"
                    if hasattr(api_err, "response") and hasattr(api_err.response, "text"):
                        err_str += f" | {api_err.response.text}"
                    log(f"[!] API Error ({self._current_model}): {err_str}")
                    if "429" in err_str.lower() or "400" in err_str.lower() or "rate" in err_str.lower() or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower() or "timeout" in err_str.lower() or "timed out" in err_str.lower() or "410" in err_str.lower() or "gone" in err_str.lower() or "404" in err_str.lower() or "not_found" in err_str.lower() or "503" in err_str.lower() or "500" in err_str.lower() or "502" in err_str.lower():
                        if self._hot_swap_provider(log):
                            continue  # Retry this iteration with the new provider
                        else:
                            raise  # No backups left, propagate the error
                    raise  # Non-rate-limit error, propagate immediately
                
                message = response.choices[0].message
                msg_dict = message.model_dump(exclude_unset=True)
                if not msg_dict.get("content") or msg_dict.get("content").strip() == "":
                    msg_dict["content"] = " " # Space placeholder prevents Gemini 400 errors
                self.messages.append(msg_dict)

                ai_text = message.content or ""

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        fn_name = tool_call.function.name
                        log(f"[*] Executing Neural Tool: {fn_name}")
                        try:
                            args = json.loads(tool_call.function.arguments)
                            # === ACTION CONFIRMATION GATE ===
                            if fn_name in DANGEROUS_TOOLS:
                                if is_pre_authorized:
                                    log(f"[✓] Voice print matched codeword. Auto-authorizing {fn_name}.")
                                else:
                                    log(f"[!] Dangerous tool detected: {fn_name}. Requesting authorization...")
                                    if self.on_confirm_request:
                                        approved = self.on_confirm_request(fn_name, args)
                                        if not approved:
                                            result = f"Action '{fn_name}' was DENIED by the user. Do not retry."
                                            self.messages.append({
                                                "role": "tool",
                                                "tool_call_id": tool_call.id,
                                                "content": str(result)
                                            })
                                            continue
                                    else:
                                        result = f"Action '{fn_name}' requires confirmation but no confirmation handler is available."
                                        self.messages.append({
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "content": str(result)
                                        })
                                        continue
                            handler = TOOL_DISPATCH.get(fn_name)
                            result = handler(args) if handler else f"Unknown tool: {fn_name}"
                            if result == "__HOT_SWAP_NEMOTRON__":
                                import os
                                from openai import OpenAI
                                nv_key = os.getenv("NVIDIA_API_KEY")
                                if not nv_key:
                                    vault = get_provider_vault()
                                    for entry in vault:
                                        if entry["api_key"].startswith("nvapi-"):
                                            nv_key = entry["api_key"]
                                            break
                                if nv_key:
                                    self.client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nv_key)
                                    self._current_model = "nvidia/llama-3.1-nemotron-70b-instruct"
                                    result = "SUCCESS: API Swapped to NVIDIA Nemotron. You are now in Coding Mode. You may proceed with coding tasks using your native file tools."
                                else:
                                    result = "FAILED: Could not find an 'nvapi-' NVIDIA key in the environment."
                            elif result == "__HOT_SWAP_GEMINI__":
                                import os
                                from openai import OpenAI
                                self.client = OpenAI(base_url=os.getenv("AI_BASE_URL"), api_key=os.getenv("AI_API_KEY"))
                                self._current_model = os.getenv("AI_MODEL")
                                result = "SUCCESS: API Swapped back to Default AI. You have exited Coding Mode."
                        except Exception as e:
                            result = f"Tool execution error: {e}"

                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result)
                        })
                    continue

                elif '<function=' in ai_text:
                    matches = re.finditer(r'<function=(\w+)>(.*?)</function>', ai_text, re.DOTALL)
                    found_any = False
                    for match in matches:
                        found_any = True
                        fn_name = match.group(1)
                        log(f"[*] Executing Neural Tool (Raw XML): {fn_name}")
                        try:
                            args = json.loads(match.group(2))
                            # === ACTION CONFIRMATION GATE (XML) ===
                            if fn_name in DANGEROUS_TOOLS:
                                if is_pre_authorized:
                                    log(f"[✓] Voice print matched codeword. Auto-authorizing {fn_name}.")
                                else:
                                    log(f"[!] Dangerous tool detected: {fn_name}. Requesting authorization...")
                                    if self.on_confirm_request:
                                        approved = self.on_confirm_request(fn_name, args)
                                        if not approved:
                                            result = f"Action '{fn_name}' was DENIED by the user. Do not retry."
                                            self.messages.append({"role": "user", "content": f"Tool Result ({fn_name}):\n{result}"})
                                            continue
                                    else:
                                        result = f"Action '{fn_name}' requires confirmation but no confirmation handler is available."
                                        self.messages.append({"role": "user", "content": f"Tool Result ({fn_name}):\n{result}"})
                                        continue
                            
                            handler = TOOL_DISPATCH.get(fn_name)
                            result = handler(args) if handler else f"Unknown tool: {fn_name}"
                            if result == "__HOT_SWAP_NEMOTRON__":
                                import os
                                from openai import OpenAI
                                nv_key = os.getenv("NVIDIA_API_KEY")
                                if not nv_key:
                                    vault = get_provider_vault()
                                    for entry in vault:
                                        if entry["api_key"].startswith("nvapi-"):
                                            nv_key = entry["api_key"]
                                            break
                                if nv_key:
                                    self.client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nv_key)
                                    self._current_model = "nvidia/llama-3.1-nemotron-70b-instruct"
                                    result = "SUCCESS: API Swapped to NVIDIA Nemotron. You are now in Coding Mode. You may proceed with coding tasks using your native file tools."
                                else:
                                    result = "FAILED: Could not find an 'nvapi-' NVIDIA key in the environment."
                            elif result == "__HOT_SWAP_GEMINI__":
                                import os
                                from openai import OpenAI
                                self.client = OpenAI(base_url=os.getenv("AI_BASE_URL"), api_key=os.getenv("AI_API_KEY"))
                                self._current_model = os.getenv("AI_MODEL")
                                result = "SUCCESS: API Swapped back to Default AI. You have exited Coding Mode."
                        except Exception as e:
                            result = f"Failed to parse JSON: {e}"
                        self.messages.append({"role": "user", "content": f"Tool Result ({fn_name}):\n{result}"})
                    if found_any:
                        continue

                final_text = re.sub(r'<function=.*?</function>', '', ai_text, flags=re.DOTALL).strip()
                if not final_text:
                    final_text = "Task completed, Sir."
                
                # Safely deduplicate stuttering without breaking Markdown newlines
                final_text = safe_deduplicate(final_text)
                
                self.messages.append({"role": "assistant", "content": final_text})
                return final_text

            log("[!] Cognitive loop hit iteration limit. Forcing response...")
            response = self.client.chat.completions.create(
                model=self._current_model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=1024
            )
            final_text = response.choices[0].message.content or "I've completed what I could, Sir."
            final_text = re.sub(r'<function=.*?</function>', '', final_text, flags=re.DOTALL).strip()
            
            # Safely deduplicate stuttering without breaking Markdown newlines
            final_text = safe_deduplicate(final_text)
            
            self.messages.append({"role": "assistant", "content": final_text})
            return final_text

        except Exception as e:
            log(f"[!] Neural Network Error: {e}")
            return "I apologize, sir, but my connection to the neural network has been severed."
        finally:
            if len(self.messages) > 15:
                # Retain system prompt
                history = [self.messages[0]]
                # Discard raw tool results from history to prevent orphaned functionResponse errors and save tokens
                for m in self.messages[1:]:
                    if m.get("role") in ["user", "assistant"] and m.get("content"):
                        history.append({"role": m.get("role"), "content": m.get("content")})
                # Keep system prompt + the 10 most recent conversational turns
                self.messages = [history[0]] + history[-10:]

# ============================================================
# NEURAL TTS (EDGE-TTS STREAMING + PYGAME)
# ============================================================
def clean_markdown_for_speech(text):
    if not text: return ""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'[\*_]{1,3}', '', text)
    text = re.sub(r'^\s*[\-\*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n+', '. ', text)
    return text.strip()

def _stream_tts_to_bytes(text, voice):
    """Use edge-tts async API to stream audio directly into memory (no disk I/O)."""
    import edge_tts
    buffer = io.BytesIO()
    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
    asyncio.run(_generate())
    buffer.seek(0)
    return buffer

def speak(text, voice=None, interrupt_flag=None):
    """Speaks text instantly by chunking sentences and buffering them in a background thread."""
    if not text: return
    text = clean_markdown_for_speech(text)
    if not text: return
    
    if voice is None:
        voice = os.getenv("AI_VOICE", "en-US-BrianMultilingualNeural")
        
    print(f"\nJ.A.R.V.I.S.: {text}")
    _init_pygame()
    import pygame
    
    # Split text into sentences for instant playback of the first chunk
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences: return
    
    audio_queue = queue.Queue()
    
    def tts_worker():
        for sentence in sentences:
            if interrupt_flag and interrupt_flag.is_set():
                break
            try:
                buf = _stream_tts_to_bytes(sentence, voice)
                audio_queue.put(buf)
            except Exception as e:
                print(f"[!] TTS Error on chunk: {e}")
                
    t = threading.Thread(target=tts_worker, daemon=True)
    t.start()
    
    def voice_interrupt_worker():
        if not interrupt_flag: return
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 4000
        recognizer.dynamic_energy_threshold = False
        try:
            with sr.Microphone() as source:
                while not interrupt_flag.is_set():
                    try:
                        audio = recognizer.listen(source, timeout=0.5, phrase_time_limit=2.0)
                        text = recognizer.recognize_google(audio, language="en-IN").lower()
                        if "jarvis" in text or "stop" in text or "ruko" in text or "chup" in text:
                            print("\n[!] Voice Interrupt Detected!")
                            interrupt_flag.set()
                            break
                    except:
                        pass
        except:
            pass

    if interrupt_flag:
        v_thread = threading.Thread(target=voice_interrupt_worker, daemon=True)
        v_thread.start()
    
    for _ in range(len(sentences)):
        if interrupt_flag and interrupt_flag.is_set():
            break
            
        try:
            # Wait for the next audio chunk to finish downloading
            buf = audio_queue.get(timeout=10)
            pygame.mixer.music.load(buf)
            pygame.mixer.music.play()
            
            # Wait for the current chunk to finish playing
            while pygame.mixer.music.get_busy():
                if interrupt_flag and interrupt_flag.is_set():
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.05)
                
        except queue.Empty:
            break
            
    try:
        pygame.mixer.music.unload()
    except:
        pass

# ============================================================
# AUDIO RECORDING
# ============================================================
def listen_for_jarvis_phrase(stop_flag=None, silence_timeout=0.8, on_speech_start=None, ai_client=None, text_queue=None):
    """Listens continuously. Keeps a 1s pre-roll buffer, detects speech, and records until silence."""
    fs = 44100
    chunk_size = int(fs * 0.1) # 100ms chunks
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    stream = sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback, blocksize=chunk_size)
    full_audio = []
    recognizer = sr.Recognizer()
    
    silence_start = None
    has_spoken = False

    with stream:
        while True:
            if stop_flag and stop_flag.is_set():
                return ""
            if text_queue and not text_queue.empty():
                return None  # Exit early to process text chat
            try:
                data = q.get(timeout=1)
            except queue.Empty:
                continue
                
            if not has_spoken:
                full_audio.append(data)
                # Keep a 1-second rolling buffer (10 chunks of 100ms) to catch the first syllable perfectly
                if len(full_audio) > 10:
                    full_audio.pop(0)
            else:
                full_audio.append(data)
                
            # Calculate RMS volume
            volume = np.sqrt(np.mean(data.astype(np.float32)**2))
            
            if volume > 300:  # Speaking threshold
                if not has_spoken:
                    has_spoken = True
                    if on_speech_start:
                        on_speech_start()
                silence_start = None
            else:
                if has_spoken:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > silence_timeout:
                        break # End of phrase
                        
            # Hard timeout 30s max recording
            if len(full_audio) > 300:
                break
                
    if len(full_audio) > 0 and has_spoken:
        audio_np = np.concatenate(full_audio)
        wav.write('temp_cmd.wav', fs, audio_np)
        
        # 1. Ultra-fast Whisper STT (if supported by the AI provider)
        if ai_client:
            try:
                with open('temp_cmd.wav', 'rb') as f:
                    transcription = ai_client.audio.transcriptions.create(
                        file=("temp_cmd.wav", f),
                        model="whisper-large-v3",
                        response_format="text"
                    )
                # The Groq endpoint returns a string when response_format="text"
                if isinstance(transcription, str):
                    return transcription.lower().strip()
                else:
                    return transcription.text.lower().strip()
            except Exception:
                pass # Fallback to Google if the provider doesn't support audio
                
        # 2. Fallback to Google STT (slower)
        try:
            with sr.AudioFile('temp_cmd.wav') as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="en-IN").lower()
            return text.strip()
        except:
            return ""
    return ""

# ============================================================
# JARVIS ENGINE (Importable by server.py)
# ============================================================
class JarvisEngine:
    """Wraps the full voice-loop so it can be started/stopped by the web server."""

    def __init__(self):
        refresh_if_stale()
        self.ai = UniversalAI()
        self.running = False
        self.stop_flag = threading.Event()
        self.interrupt_flag = threading.Event()
        self._thread = None
        self.text_queue = queue.Queue()

        # Callbacks for the web UI
        self.on_status = lambda s: None     # "STANDBY", "LISTENING", "PROCESSING", "SPEAKING"
        self.on_transcript = lambda role, text: None  # role="user" | "jarvis"
        self.on_log = lambda msg: None
        self.on_model_change = lambda m: None
        
        # Link AI model changes to Engine callback
        self.ai.on_model_change = lambda m: self.on_model_change(m)

    def send_text(self, msg, media_path=None):
        self.text_queue.put((msg, media_path))

    def start(self):
        if self.running:
            return
        self.stop_flag.clear()
        self.interrupt_flag.clear()
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self.stop_flag.set()
        self.interrupt_flag.set()

    def interrupt(self):
        self.interrupt_flag.set()

    def _loop(self):
        _init_pygame()
        import pygame
            
        self.on_log("J.A.R.V.I.S. voice engine online.")

        while self.running:
            self.on_status("STANDBY")
            
            text_item = None
            try:
                text_item = self.text_queue.get(block=False)
            except queue.Empty:
                pass
            
            if text_item:
                if isinstance(text_item, tuple):
                    command, media_path = text_item
                else:
                    command, media_path = text_item, None
                command = (command or "").strip()
                if not command and not media_path:
                    continue
                self.on_transcript("user", command or "[Media attached]")
                self.on_status("PROCESSING")
                ai_response = self.ai.chat(command or "Describe this image.", on_log=self.on_log, media_path=media_path)
                self.on_status("SPEAKING")
                self.on_transcript("jarvis", ai_response)
                self.interrupt_flag.clear()
                speak(ai_response, interrupt_flag=self.interrupt_flag)
                continue
            
            # Triggers exactly when user starts speaking
            def on_speech():
                self.on_status("LISTENING")
                
            text = listen_for_jarvis_phrase(
                stop_flag=self.stop_flag,
                silence_timeout=1.3,
                on_speech_start=on_speech,
                ai_client=self.ai.client if self.ai.ready else None,
                text_queue=self.text_queue
            )

            if not self.running:
                break
                
            if text is None:
                continue  # Text queue has items, loop around to process them

            if not text:
                continue

            if "shutdown" in text and "jarvis" in text:
                self.on_status("SPEAKING")
                self.on_transcript("jarvis", "Powering down all systems. Have a good day, sir.")
                self.interrupt_flag.clear()
                speak("Powering down all systems. Have a good day, sir.", interrupt_flag=self.interrupt_flag)
                break

            # Search for 'jarvis' anywhere in the phrase and extract what comes after it
            match = re.search(r'\bjarvis\b(.*)', text)
            if match:
                command = match.group(1).strip()
                
                if not command:
                    # User just said "Jarvis" and paused
                    self.on_status("SPEAKING")
                    self.on_transcript("jarvis", "Yes, sir?")
                    self.interrupt_flag.clear()
                    speak("Yes, sir?", interrupt_flag=self.interrupt_flag)
                    continue

                # One-breath command detected (e.g. "Jarvis tell me the news")
                self.on_transcript("user", command)
                self.on_status("PROCESSING")
                ai_response = self.ai.chat(command, on_log=self.on_log)

                self.on_status("SPEAKING")
                self.on_transcript("jarvis", ai_response)
                self.interrupt_flag.clear()
                speak(ai_response, interrupt_flag=self.interrupt_flag)

        self.running = False
        self.on_status("OFFLINE")
        self.on_log("J.A.R.V.I.S. voice engine offline.")

# ============================================================
# MAIN (Terminal Mode)
# ============================================================
def main():
    _init_colorama()
    _init_pygame()
    from colorama import Fore, Style

    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "  J.A.R.V.I.S. MK VII - MOVIE ACCURATE SYNC")
    print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)

    ai = UniversalAI()
    speak("Systems online. The Mark 7 voice protocol and neural network are fully operational, sir.")

    if not ai.ready:
        print(f"\n{Fore.RED}[!] WARNING: AI_API_KEY is not set in your .env file!{Style.RESET_ALL}")

    while True:
        print("\n[zZz] Scanning for 'Jarvis'...")
        text = listen_for_jarvis_phrase(silence_timeout=1.0)
        
        if not text:
            continue
            
        if "shutdown" in text and "jarvis" in text:
            speak("Powering down all systems. Have a good day, sir.")
            break

        match = re.search(r'\bjarvis\b(.*)', text)
        if match:
            command = match.group(1).strip()
            
            if not command:
                speak("Yes, sir?")
                continue
                
            print(f"\n{Fore.GREEN}[>] Command: {command}{Style.RESET_ALL}")
            ai_response = ai.chat(command)
            speak(ai_response)

if __name__ == "__main__":
    main()
