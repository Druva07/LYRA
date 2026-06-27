import os
import subprocess
import webbrowser
import psutil
import pyperclip
from pathlib import Path
from PIL import ImageGrab
import datetime
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
from _ctypes import COMError
try:
    from comtypes import CLSCTX_ALL
except ImportError:
    pass

# System Control Capabilities (Gemini Tools)

def open_app(name: str) -> str:
    """Opens an application. E.g., open_app('notepad')"""
    try:
        # On Windows, 'start' command handles many app names if they are in PATH or registered
        os.system(f"start {name}")
        return f"Attempted to open '{name}'."
    except Exception as e:
        return f"Failed to open '{name}': {e}"

def close_app(name: str) -> str:
    """Closes an application by process name. E.g., close_app('notepad.exe')"""
    try:
        killed = False
        name_lower = name.lower()
        if not name_lower.endswith('.exe'):
            name_lower += '.exe'
            
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == name_lower:
                proc.kill()
                killed = True
                
        if killed:
            return f"Closed '{name}'."
        return f"Could not find running process '{name}'."
    except Exception as e:
        return f"Failed to close '{name}': {e}"

def list_open_apps() -> str:
    """Returns a list of currently running application process names."""
    try:
        from lyra.system.context import get_active_apps
        return get_active_apps()
    except Exception as e:
        return f"Error: {e}"

def open_url(url: str) -> str:
    """Opens a URL in the default web browser."""
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Failed to open URL: {e}"

def search_web(query: str, engine: str = "google") -> str:
    """Searches the web for a query using the specified engine (google, duckduckgo, youtube)."""
    try:
        engine = engine.lower()
        if engine == "duckduckgo":
            url = f"https://duckduckgo.com/?q={query}"
        elif engine == "youtube":
            url = f"https://www.youtube.com/results?search_query={query}"
        else:
            url = f"https://www.google.com/search?q={query}"
            
        webbrowser.open(url)
        return f"Searched {engine} for: '{query}'"
    except Exception as e:
        return f"Failed to search web: {e}"

def open_new_tab(url: str) -> str:
    """Opens a URL in a new tab of the default web browser."""
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        webbrowser.open_new_tab(url)
        return f"Opened {url} in a new tab."
    except Exception as e:
        return f"Failed to open new tab: {e}"

def open_file(path: str) -> str:
    """Opens a file with its default application. Path must be absolute."""
    try:
        os.startfile(path)
        return f"Opened file: {path}"
    except Exception as e:
        return f"Failed to open file: {e}"

def find_file(name: str) -> str:
    """Searches for a file by name starting from the user's home directory. Note: This can be slow."""
    try:
        home = Path.home()
        # Limited search to avoid freezing for too long. We'll check Documents, Desktop, Downloads first.
        dirs_to_check = [home / "Documents", home / "Desktop", home / "Downloads"]
        
        found = []
        for d in dirs_to_check:
            if not d.exists():
                continue
            for p in d.rglob(f"*{name}*"):
                found.append(str(p))
                if len(found) >= 5: # Limit to 5 results
                    break
            if len(found) >= 5:
                break
                
        if found:
            return "Found files:\n" + "\n".join(found)
        return f"Could not find any file matching '{name}' in standard user directories."
    except Exception as e:
        return f"Error finding file: {e}"

def list_recent_files() -> str:
    """Returns a list of recently accessed files."""
    try:
        from lyra.system.context import get_recent_files
        return get_recent_files()
    except Exception as e:
        return f"Error: {e}"

def get_system_info() -> str:
    """Returns current CPU, RAM, and Disk usage."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        info = (
            f"CPU Usage: {cpu}%\n"
            f"RAM Usage: {ram.percent}% (Used: {ram.used / (1024**3):.1f}GB / Total: {ram.total / (1024**3):.1f}GB)\n"
            f"Disk Usage (C:): {disk.percent}% (Free: {disk.free / (1024**3):.1f}GB)"
        )
        return info
    except Exception as e:
        return f"Failed to get system info: {e}"

def set_volume(level: int) -> str:
    """Sets the system master volume (0 to 100)."""
    try:
        level = max(0, min(100, int(level))) # clamp between 0-100
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # pycaw uses a scalar from 0.0 to 1.0 for volume level
        scalar_vol = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar_vol, None)
        return f"Volume set to {level}%."
    except Exception as e:
        return f"Failed to set volume: {e}"

def take_screenshot() -> str:
    """Takes a screenshot and saves it to the user's Pictures directory."""
    try:
        pic_dir = Path.home() / "Pictures" / "lyra_screenshots"
        pic_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = pic_dir / filename
        
        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        return f"Screenshot saved to: {filepath}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"

def run_command(cmd: str) -> str:
    """Executes a shell command and returns the output. USE WITH CAUTION."""
    try:
        # Note: the main loop should intercept this for confirmation,
        # but if executed, it runs here.
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        
        if not output.strip():
            return "Command executed successfully with no output."
        
        if len(output) > 2000:
            return output[:2000] + "\n...[Output truncated]"
        return output
    except subprocess.TimeoutExpired:
        return f"Command '{cmd}' timed out after 10 seconds."
    except Exception as e:
        return f"Failed to run command '{cmd}': {e}"

def get_clipboard() -> str:
    """Returns the current text in the clipboard."""
    try:
        content = pyperclip.paste()
        if not content:
            return "Clipboard is empty."
        return content
    except Exception as e:
        return f"Failed to get clipboard: {e}"

def set_clipboard(text: str) -> str:
    """Copies text to the clipboard."""
    try:
        pyperclip.copy(text)
        return "Successfully copied to clipboard."
    except Exception as e:
        return f"Failed to set clipboard: {e}"

# List of all available tool functions to pass to Gemini
AVAILABLE_TOOLS = [
    open_app, close_app, list_open_apps,
    open_url, search_web, open_new_tab,
    open_file, find_file, list_recent_files,
    get_system_info, set_volume, take_screenshot,
    run_command, get_clipboard, set_clipboard
]
