import threading
import speech_recognition as sr
import pyttsx3

from src.utils.logger import logger


def speak(text: str):
    if not text:
        return False

    user_interrupted = threading.Event()
    stop_watching = threading.Event()

    engine = pyttsx3.init()
    engine.say(text)

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    def _watch_for_interruption():
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source,duration=0.3)
                while not stop_watching.is_set():
                    try:
                        recognizer.listen(source, timeout=0.5, phrase_time_limit=2)

                        user_interrupted.set()
                        stop_watching.set()
                        engine.stop()
                        logger.info("Javid 0.5 interrupted by user speech.")
                    except sr.WaitTimeoutError:
                        continue
        except Exception as e:
            logger.warning(f"Interrupt watcher error: {e}")

    watcher = threading.Thread(target=_watch_for_interruption, daemon=True)
    watcher.start()

    try:
        engine.runAndWait()
    finally:
        stop_watching.set()
        engine.stop()

    watcher.join()

    return user_interrupted.is_set()