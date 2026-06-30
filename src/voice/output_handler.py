import asyncio
import os
import tempfile
import threading

import pygame
import pyttsx3
import speech_recognition as sr

try:
    import edge_tts
except ImportError:
    edge_tts = None

from src.utils.logger import logger

EDGE_VOICE = "ar-EG-SalmaNeural"
EDGE_RATE = "+0%"


def _start_interrupt_watcher(stop_watching: threading.Event,
                             user_interrupted: threading.Event,
                             on_interrupt=None):
    """Spawns a thread that listens on the mic and flags interruption if the
    user starts speaking while JARVIS is talking."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    def _watch():
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                while not stop_watching.is_set():
                    try:
                        recognizer.listen(source, timeout=0.5, phrase_time_limit=2)
                        user_interrupted.set()
                        stop_watching.set()
                        if on_interrupt:
                            on_interrupt()
                        logger.info("Javid 0.5 interrupted by user speech.")
                    except sr.WaitTimeoutError:
                        continue
        except Exception as e:
            logger.warning(f"Interrupt watcher error: {e}")

    t = threading.Thread(target=_watch, daemon=True)
    t.start()
    return t


def _speak_pyttsx3(text: str, stop_watching: threading.Event, user_interrupted: threading.Event) -> bool:
    engine = pyttsx3.init()
    engine.say(text)

    watcher = _start_interrupt_watcher(stop_watching, user_interrupted, on_interrupt=engine.stop)

    try:
        engine.runAndWait()
    finally:
        stop_watching.set()
        engine.stop()
    watcher.join()
    return user_interrupted.is_set()

async def _generate_edge_audio(text: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice=EDGE_VOICE, rate=EDGE_RATE)
    await communicate.save(out_path)


def _speak_edge(text: str, stop_watching: threading.Event, user_interrupted: threading.Event) -> bool:
    tmp_path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name

    try:
        asyncio.run(_generate_edge_audio(text, tmp_path))

        watcher = _start_interrupt_watcher(stop_watching, user_interrupted)

        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        clock = pygame.time.Clock()
        while pygame.mixer.music.get_busy():
            if user_interrupted.is_set():
                pygame.mixer.music.stop()
                break
            clock.tick(15)

        stop_watching.set()
        watcher.join()

    finally:
        try:
            pygame.mixer.music.unload()
            pygame.mixer.quit()
        except Exception:
            pass
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return user_interrupted.is_set()


def speak(text: str) -> bool:
    """
    Speak `text` aloud. Returns True if the user interrupted (barged in)
    while JARVIS was talking, False otherwise.
    """
    if not text:
        return False

    if edge_tts is not None:
        try:
            return _speak_edge(text, threading.Event(), threading.Event())
        except Exception as e:
            logger.warning(f"edge-tts failed ({e}), falling back to pyttsx3.")

    return _speak_pyttsx3(text, threading.Event(), threading.Event())
