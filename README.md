# LYRA - Logical Yielding Reasoning Agent

LYRA is a JARVIS-style AI terminal assistant built in Python. She operates entirely within your terminal using a sleek Text User Interface (TUI) and gives you voice-activated control over your local system.

Powered by Google's latest **Gemini 3.1 Flash Lite** model, LYRA is fast, context-aware, and highly capable.

## Features
- **Local Voice Transcription (STT)**: Uses OpenAI's `whisper` model to listen to your commands locally without sending audio to the cloud.
- **Natural Text-to-Speech (TTS)**: Speaks back to you in a warm British accent using Microsoft's `edge-tts`.
- **System Awareness**: Automatically parses your PowerShell history, recent files, active applications, and clipboard content to provide rich context to the AI.
- **System Control (Tool Use)**: LYRA can search the web, open/close applications, fetch system diagnostics, take screenshots, and execute terminal commands.
- **Elegant TUI**: Rendered beautifully in the terminal using the `rich` library.

## Requirements
- Python 3.10+
- A Google Gemini API Key

## Installation & Usage
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/lyra.git
   cd lyra
   ```
2. Create your `.env` file:
   - Rename `.env.example` to `.env` (or just edit the `.env` file if it's there).
   - Paste your API key: `GEMINI_API_KEY=your_actual_api_key_here`

3. Run the one-click launcher (Windows):
   ```powershell
   .\run_lyra.ps1
   ```
   *Note: On the first run, it will automatically create a virtual environment (`.venv`), install all dependencies from `requirements.txt`, and download the Whisper base model (~140MB).*

## How to interact
Once LYRA is online, simply press and **hold the F2 key** to speak your command. Release the key, and LYRA will transcribe, think, and respond. You can also type text directly into the terminal if you prefer.

---
*Built with Gemini 3.1 Flash Lite.*
