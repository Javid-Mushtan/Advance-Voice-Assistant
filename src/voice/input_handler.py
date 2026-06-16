import speech_recognition as sr
from openai import OpenAI
from src.utils.config import OPENROUTER_API_KEY
from src.utils.logger import logger

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

def listen() -> str | None:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        logger.info("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            logger.warning("No speech detected")
            return None

    try:
        with open("temp_audio.wav","wb") as f:
            f.write(audio.get_wav_data())
        with open("temp_audio.wav","rb") as f:
            transcript = recognizer.recognize_google(audio)
        logger.info(f"You said: {transcript}")
        return transcript.strip().lower()
    except Exception as ex:
        logger.error(f"Transcription error: {ex}")
        return None