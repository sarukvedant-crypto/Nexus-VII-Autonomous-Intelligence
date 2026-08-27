import os
import json
import difflib
import subprocess
import glob
import time
import winreg
from pathlib import Path

CACHE_FILE = "app_cache.json"

def get_powershell_startapps():
    """Returns a list of dicts: {"name": str, "path": str, "source": str}"""
    apps = []
    try:
        # Get-StartApps returns Name and AppID. AppID can sometimes be a path, but often a UMIC
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if output.strip():
            data = json.loads(output)
            if not isinstance(data, list):
                data = [data]
            for item in data:
                name = item.get("Name", "")
                appid = item.get("AppID", "")
                # Only keep if AppID looks like a path, otherwise we'll rely on Start Menu links
                if os.path.exists(appid) and appid.lower().endswith(".exe"):
                    apps.append({"name": name, "path": appid, "source": "powershell_startapps"})
                elif appid and not os.path.exists(appid) and not appid.lower().endswith(".exe"):
                    apps.append({"name": name, "path": f"shell:AppsFolder\\{appid}", "source": "uwp"})
    except Exception as e:
        pass
    return apps

def get_start_menu_lnks():
    apps = []
    script = """
    $dirs = @(
        "$env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
        "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs",
        "$env:USERPROFILE\\Desktop",
        "$env:PUBLIC\\Desktop"
    )
    $shell = New-Object -ComObject WScript.Shell
    $results = @()
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            $files = Get-ChildItem -Path $dir -Include "*.lnk", "*.url" -Recurse -File -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                try {
                    if ($file.Extension -eq ".url") {
                        $results += @{
                            name = $file.BaseName
                            path = $file.FullName
                            source = "desktop_url"
                        }
                    } else {
                        $target = $shell.CreateShortcut($file.FullName).TargetPath
                        if ($target -match "\\.exe$") {
                            $results += @{
                                name = $file.BaseName
                                path = $file.FullName
                                source = "desktop_lnk"
                            }
                        }
                    }
                } catch {}
            }
        }
    }
    $results | ConvertTo-Json -Depth 2
    """
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if output.strip():
            data = json.loads(output)
            if not isinstance(data, list):
                data = [data]
            for item in data:
                if os.path.exists(item.get("path", "")):
                    apps.append(item)
    except Exception:
        pass
    return apps

def get_registry_app_paths():
    apps = []
    keys_to_check = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
    ]
    for hkey, subkey in keys_to_check:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        app_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, app_key_name) as app_key:
                            try:
                                path, _ = winreg.QueryValueEx(app_key, "")
                                if path and os.path.exists(path) and path.lower().endswith(".exe"):
                                    name = os.path.splitext(app_key_name)[0]
                                    apps.append({"name": name, "path": path, "source": "registry"})
                            except WindowsError:
                                pass
                    except WindowsError:
                        pass
        except WindowsError:
            pass
    return apps

def get_path_apps():
    apps = []
    path_env = os.environ.get("PATH", "")
    for p in path_env.split(os.pathsep):
        if not os.path.exists(p) or not os.path.isdir(p):
            continue
        try:
            for file in os.listdir(p):
                if file.lower().endswith(".exe"):
                    name = os.path.splitext(file)[0]
                    path = os.path.join(p, file)
                    apps.append({"name": name, "path": path, "source": "system_path"})
        except Exception:
            pass
    return apps

def build_app_cache():
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILE)
    apps = []
    
    # 1. PowerShell StartApps
    apps.extend(get_powershell_startapps())
    # 2. Registry App Paths
    apps.extend(get_registry_app_paths())
    # 3. Start Menu Links
    apps.extend(get_start_menu_lnks())
    # 4. PATH dirs
    apps.extend(get_path_apps())
    
    # Deduplicate by normalized name (lowercase)
    unique_apps = {}
    source_counts = {}
    
    for app in apps:
        norm_name = app["name"].lower()
        if not norm_name:
            continue
        if norm_name not in unique_apps:
            unique_apps[norm_name] = {
                "name": norm_name,
                "display_name": app["name"],
                "path": app["path"],
                "source": app["source"]
            }
            source_counts[app["source"]] = source_counts.get(app["source"], 0) + 1
            
    print(f"App Locator built cache. Sources:")
    for src, count in source_counts.items():
        print(f"  {src}: {count} apps")
        
    result = list(unique_apps.values())
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    return result

def _load_cache():
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILE)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def refresh_if_stale():
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILE)
    try:
        if not os.path.exists(cache_path):
            build_app_cache()
            return
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime > 24 * 3600:
            build_app_cache()
    except Exception as e:
        print(f"Failed to refresh app cache: {e}")

def find_app(query):
    apps = _load_cache()
    if not apps:
        return None
        
    query = query.lower()
    app_names = [a["name"] for a in apps]
    
    # Try exact match first
    for a in apps:
        if a["name"] == query or a["display_name"].lower() == query:
            return a["path"]
            
    # Fuzzy match
    matches = difflib.get_close_matches(query, app_names, n=1, cutoff=0.4)
    if matches:
        match_name = matches[0]
        for a in apps:
            if a["name"] == match_name:
                return a["path"]
                
    # Substring match fallback (query in name OR name in query)
    for a in apps:
        if query in a["name"] or a["name"] in query:
            return a["path"]
            
    return None

def get_suggestions(query, n=3):
    apps = _load_cache()
    if not apps:
        return []
    app_names = [a["display_name"] for a in apps]
    return difflib.get_close_matches(query, app_names, n=n, cutoff=0.2)
