import whisper
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import tempfile
import os
import logging
import threading

class STTEngine:
    def __init__(self):
        logging.info("Loading Whisper base model (this may take a moment on first run)...")
        # Suppress whisper warnings
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        
        self.model = whisper.load_model("base")
        self.fs = 16000  # Whisper expects 16kHz
        self.recording = False
        self.audio_data = []
        self.stream = None

    def audio_callback(self, indata, frames, time, status):
        """This is called for each audio block by sounddevice."""
        if status:
            logging.warning(f"Audio status: {status}")
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        """Starts listening to the microphone."""
        self.recording = True
        self.audio_data = []
        self.stream = sd.InputStream(samplerate=self.fs, channels=1, callback=self.audio_callback, dtype='float32')
        self.stream.start()

    def stop_recording(self) -> str:
        """Stops recording and returns the transcribed text."""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_data:
            return ""

        # Concatenate all recorded blocks (shape N, 1) and flatten to (N,)
        audio_np = np.concatenate(self.audio_data, axis=0).flatten()
        
        try:
            # Transcribe directly from numpy array (bypasses ffmpeg requirement)
            result = self.model.transcribe(audio_np)
            text = result["text"].strip()
            return text
        except Exception as e:
            logging.error(f"STT Error: {e}")
            return ""
