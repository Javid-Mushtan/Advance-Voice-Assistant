from src.voice.input_handler import listen
from src.voice.output_handler import speak
from src.brain.agent_graph import agent_graph, AgentState
from src.brain.memory import LongTermMemory
from langchain_core.messages import HumanMessage

def main():
    print("Initializing Jarvis...")
    memory = LongTermMemory()
    session_id = "jarvis_user"
    state = AgentState(
        messages=[],
        session_id=session_id,
        long_term_memory=memory
    )

    speak("Hello, I am Jarvis. How can I help you?")
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
            # The last message should be an AIMessage with the final answer
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