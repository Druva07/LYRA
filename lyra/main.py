import os
import sys
import time
import queue
import threading
from dotenv import load_dotenv
from pynput import keyboard
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm

# Ensure LYRA is in PYTHONPATH so absolute imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lyra.ai.gemini import LyraAI
from lyra.audio.stt import STTEngine
from lyra.audio.tts import TTSEngine

console = Console()
input_queue = queue.Queue()

def run_command_confirmation(cmd: str) -> bool:
    """Callback for Gemini to ask user confirmation before running a shell command."""
    # This might run in the same thread, so we can just prompt
    console.print(Panel(f"[yellow]LYRA wants to run the following command:[/yellow]\n\n[bold white]{cmd}[/bold white]", title="Command Execution Request", border_style="yellow"))
    return Confirm.ask("[bold red]Allow execution?[/bold red]")

def handle_input(text: str, ai: LyraAI, tts: TTSEngine):
    """Processes the transcribed text."""
    text = text.strip()
    if not text:
        return

    # Clean up common STT hallucinations or prefixes
    text_lower = text.lower()
    
    # Print user input
    console.print(f"[bold green]You:[/bold green] {text}")

    # Handle local commands
    if text_lower == "exit" or text_lower == "quit":
        console.print("[bold cyan]LYRA:[/bold cyan] Goodbye, sir.")
        tts.speak("Goodbye, sir.")
        time.sleep(1.5)
        os._exit(0)
        
    if "lyra forget that" in text_lower or "forget that" in text_lower:
        response = ai.forget_last()
        console.print(f"[bold cyan]LYRA:[/bold cyan] {response}")
        tts.speak(response)
        return
        
    if "lyra refresh context" in text_lower or "refresh context" in text_lower:
        ai.refresh_context()
        response = "System context refreshed."
        console.print(f"[bold cyan]LYRA:[/bold cyan] {response}")
        tts.speak(response)
        return

    # Process with Gemini
    with console.status("[cyan]LYRA is thinking...[/cyan]"):
        response = ai.send_message_with_tools(text, ask_confirmation_callback=run_command_confirmation)
    
    # Print and speak
    console.print(Panel(Markdown(response), title="LYRA", border_style="cyan"))
    tts.speak(response)

def main():
    console.clear()
    console.print(Panel("[bold cyan]Initializing LYRA (Logical Yielding Reasoning Agent)...[/bold cyan]\nLoading models and system context...", border_style="cyan"))
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check API key early
    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "paste_your_api_key_here":
        console.print("[bold red]ERROR: GEMINI_API_KEY environment variable is not set.[/bold red]")
        console.print("Please paste your API key into the [bold].env[/bold] file and try again.")
        sys.exit(1)

    ai = LyraAI()
    stt = STTEngine()
    tts = TTSEngine()
    
    console.print("[bold green]LYRA is online.[/bold green]")
    console.print("Hold [bold yellow]F2[/bold yellow] to speak. Release to send. Or type 'exit' to quit.\n")
    
    # Hotkey state
    is_f2_pressed = False

    def on_press(key):
        nonlocal is_f2_pressed
        if key == keyboard.Key.f2 and not is_f2_pressed:
            is_f2_pressed = True
            stt.start_recording()
            console.print("\r[bold red]Listening... (Release F2 to stop)[/bold red]", end="")

    def on_release(key):
        nonlocal is_f2_pressed
        if key == keyboard.Key.f2:
            is_f2_pressed = False
            console.print("\r[bold yellow]Transcribing...[/bold yellow]               ", end="\r")
            text = stt.stop_recording()
            if text:
                input_queue.put(text)
            else:
                console.print("\r[dim]No speech detected.[/dim]                  ", end="\r\n")

    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    # Start text input listener
    def text_input_worker():
        while True:
            try:
                # This will block waiting for Enter
                text = input()
                if text.strip():
                    input_queue.put(text.strip())
            except EOFError:
                break
            except Exception:
                pass

    threading.Thread(target=text_input_worker, daemon=True).start()
    
    tts.speak("Lyra is online and ready.")

    # Main loop
    try:
        while True:
            # Check for typed commands just in case (non-blocking if possible, but input() blocks)
            # Since input() blocks, we rely on the queue. We can use a timeout.
            try:
                text = input_queue.get(timeout=0.1)
                handle_input(text, ai, tts)
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[bold cyan]Shutting down LYRA...[/bold cyan]")
        listener.stop()
        if hasattr(stt, 'stream') and stt.stream:
            stt.stream.stop()
            stt.stream.close()

if __name__ == "__main__":
    main()
