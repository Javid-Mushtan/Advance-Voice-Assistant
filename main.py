import random
import time
from datetime import datetime

import ollama

from src.brain.macro_engine import macro_scheduler
from src.voice.input_handler import listen
from src.voice.output_handler import speak
from src.brain.agent_graph import agent_graph, AgentState
from src.brain.memory import LongTermMemory
from langchain_core.messages import HumanMessage

macro_scheduler.start()

def get_greeting(name="Javid 0.5"):
    hour = datetime.now().hour

    if 5 <= hour < 12:
        time_greetings = [
            "Good morning",
            "Morning",
            "Rise and shine",
            "Top of the morning"
        ]
    elif 12 <= hour < 17:
        time_greetings = [
            "Good afternoon",
            "Hey there",
            "Hope your day is going well",
            "Good day"
        ]
    elif 17 <= hour < 21:
        time_greetings = [
            "Good evening",
            "Evening",
            "Hope you had a productive day",
            "Nice to see you this evening"
        ]
    else:
        time_greetings = [
            "Good night",
            "Hello night explorer",
            "Burning the midnight oil, I see",
            "Late night session detected"
        ]

    personality_openers = [
        "Javid 0.5 online.",
        "Assistant core is active.",
        "Voice system initialized.",
        "Ready for your command.",
        "AI brain warmed up."
    ]

    greeting = random.choice(time_greetings)
    opener = random.choice(personality_openers)

    response = ollama.chat(
        model="gpt-oss:20b",
        messages=[
            {
                "role": "system",
                "content": f"""
                You are an advanced AI voice assistant.
            
                Startup message:
                "{time.time()} {greeting}, {name}. {opener} How can I help you?"
            
                Behavior rules:
                - Name is important
                - Be natural and conversational
                - Avoid repeating same phrases
                - Act like a real assistant speaking to the user
                """
            },
            {
                "role": "user",
                "content": "Start the conversation with creativly."
            }
        ]
    )

    return response["message"]["content"]


def main():
    print("Initializing Javid 0.5...")
    memory = LongTermMemory()
    session_id = "Javid 0.5"
    state = AgentState(
        messages=[],
        session_id=session_id,
        long_term_memory=memory
    )

    speak(get_greeting("JAVID 0.5"))
    while True:
        try:
            user_input = listen()
            if not user_input:
                continue
            if user_input in ["exit", "quit", "goodbye", "bye"]:
                speak("Goodbye!")
                break

            state["messages"].append(HumanMessage(content=user_input))
            state = agent_graph.invoke(state)
            last_msg = state["messages"][-1]
            if hasattr(last_msg, "content") and last_msg.content:
                answer = last_msg.content
                print(f"Jarvis: {answer}")
                speak(answer)
            else:
                speak("I'm not sure how to respond to that.")
        except KeyboardInterrupt:
            speak("Shutting down.")
            break
        except Exception as e:
            print(f"Error: {e}")
            speak("An error occurred. Please try again.")

if __name__ == "__main__":
    main()