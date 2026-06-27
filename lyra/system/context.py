import os
import shutil
import sqlite3
import tempfile
import psutil
import pyperclip
from pathlib import Path

def get_shell_history() -> str:
    """Reads PowerShell history and returns the last 200 commands."""
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return "Shell history unavailable (APPDATA not found)."
    
    history_path = Path(appdata) / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt"
    if not history_path.exists():
        return "PowerShell history file not found."
        
    try:
        with open(history_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        last_200 = [line.strip() for line in lines[-200:] if line.strip()]
        if not last_200:
            return "Shell history is empty."
            
        return "\n".join(last_200)
    except Exception as e:
        return f"Error reading shell history: {e}"

def get_recent_files() -> str:
    """Reads Windows Recent files and returns the last 30."""
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return "Recent files unavailable (APPDATA not found)."
        
    recent_dir = Path(appdata) / "Microsoft" / "Windows" / "Recent"
    if not recent_dir.exists():
        return "Recent files directory not found."
        
    try:
        # Get .lnk files sorted by modification time descending
        lnk_files = sorted(recent_dir.glob('*.lnk'), key=lambda p: p.stat().st_mtime, reverse=True)
        recent = [f.stem for f in lnk_files[:30]]
        if not recent:
            return "No recent files found."
            
        return "\n".join(recent)
    except Exception as e:
        return f"Error reading recent files: {e}"

def get_browser_history() -> str:
    """Reads Chrome history and returns the last 50 visited URLs/Titles."""
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        return "Chrome history unavailable (LOCALAPPDATA not found)."
        
    chrome_history_path = Path(localappdata) / "Google" / "Chrome" / "User Data" / "Default" / "History"
    if not chrome_history_path.exists():
        return "Chrome history file not found."
        
    temp_db = None
    try:
        # Copy to temp file to avoid locking issues
        temp_fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(temp_fd)
        shutil.copy2(chrome_history_path, temp_path)
        temp_db = temp_path
        
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        
        # Query history
        query = """
            SELECT urls.url, urls.title
            FROM urls JOIN visits ON urls.id = visits.url
            ORDER BY visits.visit_time DESC
            LIMIT 50
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No browser history found."
            
        history = [f"- {title[:50]}... ({url})" if len(title) > 50 else f"- {title} ({url})" for url, title in rows]
        return "\n".join(history)
    except Exception as e:
        return f"Error reading browser history: {e}"
    finally:
        if temp_db and os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

def get_active_apps() -> str:
    """Lists running application process names (deduplicated)."""
    try:
        apps = set()
        for proc in psutil.process_iter(['name']):
            name = proc.info['name']
            if name and name.endswith('.exe'):
                apps.add(name)
        
        # Filter out some very common system processes to keep the list useful
        system_procs = {'svchost.exe', 'conhost.exe', 'csrss.exe', 'wininit.exe', 'services.exe', 'lsass.exe', 'smss.exe'}
        filtered = [app for app in apps if app.lower() not in system_procs]
        
        return "\n".join(sorted(filtered))
    except Exception as e:
        return f"Error reading active apps: {e}"

def get_clipboard_content() -> str:
    """Reads current clipboard content."""
    try:
        content = pyperclip.paste()
        if not content:
            return "Clipboard is empty."
        # Truncate if too long
        if len(content) > 1000:
            return content[:1000] + "\n...[truncated]"
        return content
    except Exception as e:
        return f"Error reading clipboard: {e}"

def build_context_string() -> str:
    """Consolidates system context into a markdown string for Gemini."""
    context = [
        "## SYSTEM CONTEXT & HISTORY",
        "This information represents the user's recent computer activity.",
        "",
        "### Recent Shell Commands (PowerShell)",
        get_shell_history(),
        "",
        "### Recently Opened Files",
        get_recent_files(),
        "",
        "### Recent Browser History (Chrome)",
        get_browser_history(),
        "",
        "### Active Applications (Processes)",
        get_active_apps(),
        "",
        "### Current Clipboard Content",
        get_clipboard_content(),
        ""
    ]
    return "\n".join(context)
