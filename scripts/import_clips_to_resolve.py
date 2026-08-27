"""
import_clips_to_resolve.py

Python script to import all MP4 clips from a specified directory into the currently open
DaVinci Resolve project media pool.

Primary Method: DaVinci Resolve Scripting API (DaVinciResolveScript)
Fallback Method: PyAutoGUI GUI Automation (Hotkey Ctrl+I / Ctrl+Shift+I)

Target Directory: (configurable via TARGET_DIR variable)
"""

import os
import sys
import time
import glob
import ctypes
from pathlib import Path

# Target directory containing MP4 clips
# Set TARGET_DIR to your folder containing MP4 clips
TARGET_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "resolve_clips")


def copy_to_clipboard(text: str) -> bool:
    """Copies text to the Windows Clipboard using pyperclip or ctypes."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        # Fallback to Windows API via ctypes
        try:
            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            user32.OpenClipboard(0)
            user32.EmptyClipboard()
            
            encoded = text.encode('utf-16le') + b'\x00\x00'
            h_mem = kernel32.GlobalAlloc(0x0042, len(encoded))
            p_mem = kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, encoded, len(encoded))
            kernel32.GlobalUnlock(h_mem)
            
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            user32.CloseClipboard()
            return True
        except Exception as e:
            print(f"[Warning] Failed to copy to clipboard: {e}")
            return False


def focus_davinci_resolve() -> bool:
    """Finds and brings the DaVinci Resolve window to the foreground."""
    user32 = ctypes.windll.user32
    found_hwnd = None

    def enum_windows_proc(hwnd, lParam):
        nonlocal found_hwnd
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value
            if "davinci resolve" in title.lower() and user32.IsWindowVisible(hwnd):
                found_hwnd = hwnd
                return False  # Stop enumeration
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ssize_t, ctypes.c_ssize_t)
    user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)

    if found_hwnd:
        SW_RESTORE = 9
        user32.ShowWindow(found_hwnd, SW_RESTORE)
        user32.SetForegroundWindow(found_hwnd)
        time.sleep(1.0)
        return True
    return False


def get_mp4_files(directory: str) -> list[str]:
    """Finds all MP4 files in the target directory (case-insensitive)."""
    if not os.path.exists(directory):
        print(f"[Error] Target directory does not exist: {directory}")
        return []

    mp4_files = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".mp4"):
                mp4_files.append(os.path.abspath(os.path.join(root, f)))
    return mp4_files


def import_via_resolve_api(mp4_files: list[str]) -> bool:
    """
    Attempts to import MP4 files using DaVinci Resolve Python Scripting API.
    Returns True if successfully imported via API, False otherwise.
    """
    print("\n--- Method 1: DaVinci Resolve Scripting API ---")

    # Standard Windows install paths for DaVinci Resolve Scripting API
    possible_api_paths = [
        os.environ.get("RESOLVE_SCRIPT_API"),
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules",
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
    ]

    for path in possible_api_paths:
        if path and os.path.exists(path) and path not in sys.path:
            sys.path.append(path)

    try:
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
        if not resolve:
            print("[API] Unable to communicate with DaVinci Resolve application.")
            print("[API] (Make sure DaVinci Resolve is running and scripting is enabled).")
            return False

        pm = resolve.GetProjectManager()
        if not pm:
            print("[API] Could not retrieve ProjectManager.")
            return False

        project = pm.GetCurrentProject()
        if not project:
            print("[API] No project currently open in DaVinci Resolve.")
            return False

        print(f"[API] Connected to active project: '{project.GetName()}'")
        media_pool = project.GetMediaPool()
        if not media_pool:
            print("[API] Could not access Media Pool.")
            return False

        print(f"[API] Importing {len(mp4_files)} MP4 file(s) into Media Pool...")
        imported_items = media_pool.ImportMedia(mp4_files)

        if imported_items:
            print(f"[API Success] Successfully imported {len(imported_items)} clip(s):")
            for item in imported_items:
                print(f"  - {item.GetName()}")
            return True
        else:
            print("[API] ImportMedia completed but returned no items.")
            return False

    except ImportError:
        print("[API] DaVinciResolveScript module not found on system paths.")
        return False
    except Exception as e:
        print(f"[API Error] Exception occurred while using Scripting API: {e}")
        return False


def import_via_gui_automation(folder_path: str, mp4_files: list[str]) -> bool:
    """
    Fallback method using PyAutoGUI to simulate GUI actions in DaVinci Resolve.
    """
    print("\n--- Method 2: PyAutoGUI GUI Automation Fallback ---")
    
    try:
        import pyautogui
    except ImportError:
        print("[GUI Error] PyAutoGUI is not installed. Please install it with: pip install pyautogui")
        return False

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5

    print("[GUI] Locating and focusing DaVinci Resolve window...")
    focused = focus_davinci_resolve()
    if not focused:
        print("[GUI Warning] Could not automatically focus DaVinci Resolve window.")
        print("[GUI] Please click on DaVinci Resolve to bring it into focus within 5 seconds...")
        time.sleep(5.0)

    print("[GUI] Focus set. Sending 'Ctrl+I' (Import Media shortcut)...")
    pyautogui.hotkey('ctrl', 'i')
    time.sleep(1.5)

    # Step 1: Copy folder path to clipboard and paste in File Name box
    print(f"[GUI] Navigating to target directory: {folder_path}")
    copy_to_clipboard(folder_path)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(1.2)

    # Step 2: Select all MP4 files in the folder
    print("[GUI] Selecting all files in folder (Ctrl+A)...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)

    # Step 3: Press Enter to open/import
    print("[GUI] Pressing Enter to confirm import...")
    pyautogui.press('enter')
    time.sleep(1.5)

    print("[GUI Success] Import command executed via GUI automation!")
    return True


def main():
    print("==================================================")
    print("  DaVinci Resolve MP4 Clip Importer")
    print("==================================================")
    print(f"Target Directory: {TARGET_DIR}\n")

    # 1. Discover MP4 files
    mp4_files = get_mp4_files(TARGET_DIR)
    if not mp4_files:
        print(f"[Warning] No MP4 files found in: {TARGET_DIR}")
        print("Checking directory status...")
        if not os.path.exists(TARGET_DIR):
            print(f"[Error] Directory does not exist on disk: {TARGET_DIR}")
            return
        else:
            print("Directory exists, but contains no .mp4 files.")
            return

    print(f"Found {len(mp4_files)} MP4 file(s):")
    for file_path in mp4_files:
        print(f"  - {os.path.basename(file_path)}")

    # 2. Try DaVinci Resolve Scripting API first
    api_success = import_via_resolve_api(mp4_files)

    # 3. Fallback to GUI automation if API fails
    if not api_success:
        print("\n[Notice] API import was not successful. Triggering PyAutoGUI fallback...")
        gui_success = import_via_gui_automation(TARGET_DIR, mp4_files)
        if not gui_success:
            print("\n[Error] Both API and GUI automation methods failed.")
        else:
            print("\n[Completed] GUI automation process finished.")
    else:
        print("\n[Completed] API import completed successfully!")


if __name__ == "__main__":
    main()
