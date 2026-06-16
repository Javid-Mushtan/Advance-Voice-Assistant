from typing import TypedDict, Annotated, Any
from langgraph.graph import StateGraph, END
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

def _rag_search_impl(query: str, session_id: str) -> str:
    """Call the history‑aware RAG pipeline."""
    try:
        result = conversational_rag_chain.invoke(
            {"input": query},
            config={"configurable": {"session_id": session_id}}
        )
        return result["answer"]
    except Exception as e:
        return f"RAG error: {str(e)}"

def _remember_fact_impl(fact: str, memory: LongTermMemory) -> str:
    memory.remember(fact)
    return "Fact remembered."

def _recall_memory_impl(query: str, memory: LongTermMemory) -> str:
    return memory.recall(query)

# ------------------------------------------------------------------
# 3. Tool wrappers for the LLM – ONLY contain JSON‑safe parameters
#    These are what the LLM will “see” and call.
# ------------------------------------------------------------------
@tool
def rag_search(query: str) -> str:
    """Search your personal knowledge base (documents). Use this when the user asks about stored documents."""
    # The real work is done by the tool executor, not here.
    return "This placeholder should never be called."

@tool
def remember_fact(fact: str) -> str:
    """Store a fact about the user in long‑term memory."""
    return "Placeholder"

@tool
def recall_memory(query: str) -> str:
    """Retrieve facts about the user from long‑term memory."""
    return "Placeholder"

bindable_tools = [
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


TOOL_IMPL_MAP = {
    "rag_search": lambda args, state: _rag_search_impl(
        query=args["query"], session_id=state["session_id"]
    ),
    "remember_fact": lambda args, state: _remember_fact_impl(
        fact=args["fact"], memory=state["long_term_memory"]
    ),
    "recall_memory": lambda args, state: _recall_memory_impl(
        query=args["query"], memory=state["long_term_memory"]
    ),
}

llm = ChatOpenAI(model="openrouter/free", temperature=0, api_key=OPENROUTER_API_KEY,base_url="https://openrouter.ai/api/v1")
llm_with_tools = llm.bind_tools(bindable_tools)

def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


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
            # If we have a special implementation that needs state, use it
            if tool_name in TOOL_IMPL_MAP:
                result = TOOL_IMPL_MAP[tool_name](args, state)
            else:
                # Generic tool – just call its .invoke() method
                tool_obj = {t.name: t for t in bindable_tools}[tool_name]
                result = tool_obj.invoke(args)
            results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        except Exception as e:
            results.append(ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"]))
    return {"messages": results}

# ------------------------------------------------------------------
# 9. Build the graph
# ------------------------------------------------------------------
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