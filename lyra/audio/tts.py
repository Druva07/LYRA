import asyncio
import edge_tts
import pygame
import pyttsx3
import tempfile
import os
import threading
import logging

class TTSEngine:
    def __init__(self):
        self.voice = "en-GB-SoniaNeural"
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Initialize pyttsx3 fallback
        self.fallback_engine = pyttsx3.init()
        # Try to find a female British voice for fallback if possible, else default
        voices = self.fallback_engine.getProperty('voices')
        for v in voices:
            if 'Zira' in v.name or 'Hazel' in v.name or 'female' in v.name.lower():
                self.fallback_engine.setProperty('voice', v.id)
                break

    async def _async_speak(self, text: str):
        """Generates speech using edge-tts and plays it."""
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            
            await communicate.save(temp_path)
            
            # Play using pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Wait until finished playing
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            pygame.mixer.music.unload()
            
            # Clean up
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"Edge-TTS failed: {e}. Falling back to pyttsx3.")
            self._fallback_speak(text)

    def _fallback_speak(self, text: str):
        """Synchronous fallback using pyttsx3."""
        try:
            self.fallback_engine.say(text)
            self.fallback_engine.runAndWait()
        except Exception as e:
            logging.error(f"Fallback TTS failed: {e}")

    def speak(self, text: str):
        """Main method to speak text. Runs asynchronously in a new thread if needed."""
        if not text:
            return
            
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_speak(text))
            loop.close()
            
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        # We don't join the thread here so it doesn't block the TUI, 
        # unless we want synchronous speaking. For an assistant, async is usually better.
        # But we need to make sure we don't start multiple TTS streams at once.
        # For simplicity, returning immediately is fine.
