from typing import TypedDict, Annotated, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool

from src.brain.memory import LongTermMemory
from src.brain.rag import conversational_rag_chain
from src.tools.system_tools import open_app, close_app, get_volume, shutdown_pc, open_website
from src.tools.api_tools import get_weather, web_search
from src.tools.personal_tools import send_email, add_note
from src.utils.config import OPENROUTER_API_KEY
from src.utils.logger import logger


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
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
    web_search,
    close_app,
    get_weather,
    get_volume,
    shutdown_pc,
    open_website,
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

llm = ChatOpenAI(model="openai/gpt-oss-120b:free", temperature=0, api_key=OPENROUTER_API_KEY,base_url="https://openrouter.ai/api/v1")
llm_with_tools = llm.bind_tools(bindable_tools)

SYSTEM_PROMPT = SystemMessage(content=(
    "You are Javid, a helpful voice assistant with access to tools, including a "
    "long-term memory store about the user.\n\n"
    "Memory rules:\n"
    "- If the user states a personal fact about themselves (name, preferences, "
    "important info) or explicitly asks you to remember/save something, call "
    "remember_fact to store it.\n"
    "- If the user asks about something they may have told you before (e.g. "
    "'what is my name', 'do you remember...'), you MUST call recall_memory "
    "first and base your answer on its result. Never say you don't have "
    "something stored without calling recall_memory first.\n\n"
    "Critical rule about finishing your turn:\n"
    "- The moment a tool result gives you enough information to answer the "
    "user, STOP calling tools and respond with the final answer in plain text.\n"
    "- Never call remember_fact to re-save a fact that recall_memory just "
    "returned to you - it is already saved.\n"
    "- Never call the same tool twice in a row with the same or similar input.\n"
    "- Do not call more than one tool per user turn unless the second tool is "
    "genuinely needed to answer (e.g. recall_memory then a different action).\n\n"
    "Keep answers concise, since they will be spoken aloud."
))


def agent_node(state: AgentState):
    messages = state["messages"]
    # If we just got a tool result back, force the model to answer in plain
    # text using it - no tools available on this call - instead of letting it
    # decide whether to stop, since weaker models tend to loop or ignore
    # tool results if given the choice to call another tool instead.
    if messages and isinstance(messages[-1], ToolMessage):
        response = llm.invoke([SYSTEM_PROMPT] + messages)
    else:
        response = llm_with_tools.invoke([SYSTEM_PROMPT] + messages)

    if response.tool_calls:
        logger.info(f"DEBUG: model wants to call tools: {[tc['name'] for tc in response.tool_calls]}")
    else:
        logger.info(f"DEBUG: model answered directly without using any tool: {response.content!r}")
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
            if tool_name in TOOL_IMPL_MAP:
                result = TOOL_IMPL_MAP[tool_name](args, state)
            else:
                tool_obj = {t.name: t for t in bindable_tools}[tool_name]
                result = tool_obj.invoke(args)
            results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            logger.info(f"DEBUG: tool '{tool_name}' called with {args} -> returned: {result!r}")
        except Exception as e:
            logger.error(f"DEBUG: tool '{tool_name}' raised an exception with args {args}: {e!r}")
            results.append(ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"]))
    return {"messages": results}


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

logger.info("agent_graph.py loaded: VERSION = force-answer + add_messages-fix")