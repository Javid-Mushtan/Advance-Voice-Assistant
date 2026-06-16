import pyttsx3


engine = pyttsx3.init()

def speak(text: str):
    engine.say(text)
    engine.runAndWait()
    engine.stop()