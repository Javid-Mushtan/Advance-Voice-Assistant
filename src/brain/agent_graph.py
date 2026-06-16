from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

from src.brain.memory import LongTermMemory
from src.brain.rag import conversational_rag_chain
from src.tools.system_tools import open_app, get_volume, shutdown_pc
from src.tools.api_tools import get_weather
from src.tools.personal_tools import send_email, add_note
from src.utils.config import OPENROUTER_API_KEY

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], "Conversation history"]
    session_id: str
    long_term_memory: LongTermMemory

# --- Wrapper tools that accept the memory object ---
# We'll define functions that extract memory from state via tool args.
# In LangGraph we can inject state via partial tool binding.

@tool
def rag_search(query: str, session_id: str) -> str:
    """Search your personal knowledge base (documents) using conversation history."""
    try:
        result = conversational_rag_chain.invoke(
            {"input": query},
            config={"configurable": {"session_id": session_id}}
        )
        return result["answer"]
    except Exception as e:
        return f"RAG error: {str(e)}"

@tool
def remember_fact(fact: str, memory_obj: LongTermMemory) -> str:
    """Store a fact about the user in long-term memory."""
    memory_obj.remember(fact)
    return "Fact remembered."

@tool
def recall_memory(query: str, memory_obj: LongTermMemory) -> str:
    """Retrieve facts about the user from long-term memory."""
    return memory_obj.recall(query)

all_tools = [
    rag_search,
    remember_fact,
    recall_memory,
    open_app,
    get_weather,
    get_volume,
    shutdown_pc,
    send_email,
    add_note,
]

llm = ChatOpenAI(model="openrouter/free",base_url="https://openrouter.ai/api/v1", temperature=0, api_key=OPENROUTER_API_KEY)
llm_with_tools = llm.bind_tools(all_tools)


def tool_executor(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    if not tool_calls:
        return {"messages": []}

    results = []
    for tc in tool_calls:
        tool_name = tc["name"]
        args = tc["args"]
        try:
            if tool_name == "rag_search":
                result = rag_search.invoke({"query": args["query"], "session_id": state["session_id"]})
            elif tool_name in ["remember_fact", "recall_memory"]:
                result = globals()[tool_name].invoke({**args, "memory_obj": state["long_term_memory"]})
            else:
                tool_func = {t.name: t for t in all_tools}[tool_name]
                result = tool_func.invoke(args)
            results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        except Exception as e:
            results.append(ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"]))
    return {"messages": results}

def agent_node(state: AgentState):
    response = tool_executor(state)
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_executor)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    lambda state: "tools" if state["messages"][-1].tool_calls else END,
    {"tools": "tools", END: END}
)

workflow.add_edge("tools", "agent")

agent_graph = workflow.compile()