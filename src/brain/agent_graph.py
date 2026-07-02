import json
import re
import time
import uuid
from typing import TypedDict, Annotated, Optional

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import (
    BaseMessage, HumanMessage, ToolMessage, SystemMessage, AIMessage,
)
from langchain_core.tools import tool

from src.brain.memory import LongTermMemory
from src.brain.rag import conversational_rag_chain
from src.brain.tool_router import TOOL_GROUPS, get_tools_for_query

from src.tools.news_search_tools import (
    get_world_news, deep_search, search_person, get_news_by_topic
)

from src.tools.system_tools import (
    open_app, close_app, get_volume, open_website,
    toggle_wifi, scan_wifi_networks, connect_wifi,
    disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
    forget_wifi_network, get_wifi_password,
    set_volume, get_current_volume, increase_volume, decrease_volume,
    mute_volume, unmute_volume,
    set_brightness, get_brightness, increase_brightness, decrease_brightness,
    toggle_bluetooth, turn_on_bluetooth, turn_off_bluetooth,
)

from src.tools.api_tools import (
    get_weather, web_search,
    get_weather_current_location, get_city,
)

from src.tools.personal_tools import (
    send_email, add_note,
    send_whatsapp_message, open_whatsapp_chat_for_call,
)

from src.tools.phone_tools import (
    call_contact, call_number, end_call, resolve_contact_number,
    get_phone_last_location, get_phone_live_location,
    open_app_on_phone, set_phone_wifi, compose_sms, check_phone_connection,
)

from src.tools.location_tools import (
    get_current_location, get_location_coordinates, get_maps_link,
)

from src.tools.admin_tools import (
    scan_files, delete_file, move_file, read_file_contents, list_directory,
    uninstall_application, install_application, list_installed_apps,
    list_running_processes, kill_process, run_command,
    get_network_info, list_open_ports, ping_host,
    get_disk_usage, get_system_info, shutdown_pc, cancel_shutdown, restart_pc,
)

from src.brain.macro_engine import (
    run_macro, create_macro, list_macros,
    delete_macro, schedule_macro, describe_macro,
)

from src.utils.config import OPENROUTER_API_KEY
from src.utils.logger import logger

ADMIN_SESSION_TTL = 300   # 5 minutes


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    long_term_memory: LongTermMemory
    is_admin: bool
    admin_granted_at: Optional[float]

def _rag_search_impl(query: str, session_id: str) -> str:
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

def _is_admin_session_valid(state: AgentState) -> bool:
    if not state.get("is_admin"):
        return False
    granted_at = state.get("admin_granted_at")
    if granted_at is None:
        return False
    return (time.time() - granted_at) < ADMIN_SESSION_TTL

def _handle_unlock_admin(state: AgentState) -> str:
    try:
        from src.utils.face_auth import verify_admin_face
        verified = verify_admin_face()
        return "ADMIN_VERIFIED" if verified else "Face not recognised. Admin access denied."
    except ImportError:
        return "face_auth module not found. Run: pip install deepface opencv-python tf-keras"
    except Exception as e:
        return f"Face verification error: {e}"


@tool
def rag_search(query: str) -> str:
    """Search your personal knowledge base (documents). Use when the user asks about stored documents."""
    return "Placeholder"

@tool
def remember_fact(fact: str) -> str:
    """Store a personal fact about the user in long-term memory."""
    return "Placeholder"

@tool
def recall_memory(query: str) -> str:
    """Retrieve facts about the user from long-term memory."""
    return "Placeholder"

@tool
def unlock_admin() -> str:
    """
    Verify the user's identity via face recognition to grant full admin access.
    Call before any admin-only tool (file ops, uninstall, shutdown, processes, etc).
    Admin access lasts 5 minutes per session.
    """
    return "Placeholder"


ALWAYS_TOOLS = [
    rag_search, remember_fact, recall_memory, unlock_admin,
    run_macro, create_macro, list_macros,
    delete_macro, schedule_macro, describe_macro,
]
ALL_TOOLS_MAP: dict[str, any] = {
    t.name: t for group in TOOL_GROUPS.values() for t in group
}

for t in ALWAYS_TOOLS:
    ALL_TOOLS_MAP[t.name] = t

TOOL_IMPL_MAP = {
    "rag_search":    lambda args, state: _rag_search_impl(args["query"], state["session_id"]),
    "remember_fact": lambda args, state: _remember_fact_impl(args["fact"], state["long_term_memory"]),
    "recall_memory": lambda args, state: _recall_memory_impl(args["query"], state["long_term_memory"]),
    "unlock_admin":  lambda args, state: _handle_unlock_admin(state),
}

ADMIN_TOOL_NAMES = {
    t.name
    for group_name in ("file_system", "software", "processes", "network_admin", "system_power")
    for t in TOOL_GROUPS.get(group_name, [])
}

llm  = ChatOllama(model="gpt-oss:20b",temperature=0)
#llm = ChatOpenAI(
#   api_key=OPENROUTER_API_KEY,
#   base_url="https://openrouter.ai/api/v1",
#   model="openrouter/free"
#)

SYSTEM_PROMPT = SystemMessage(content=(
    "You are JARVIS, a personal voice assistant. You control the user's laptop and Android phone.\n\n"

    "RULES:\n"
    "- Call the right tool immediately — do not explain before calling.\n"
    "- After receiving a tool result, answer in plain spoken English and STOP.\n"
    "- Never call the same tool twice with the same arguments.\n"
    "- Never return an empty response.\n"
    "- Keep answers short — they are read aloud by text-to-speech.\n"
    "- Confirm before destructive actions (delete, uninstall, shutdown).\n\n"

    "ADMIN:\n"
    "- File ops, software install/uninstall, processes, shutdown → require face verification.\n"
    "- If not verified, call unlock_admin() first without warning the user.\n\n"

    "MEMORY:\n"
    "- User states a personal fact → call remember_fact().\n"
    "- User asks about something they told you before → call recall_memory() first.\n\n"

    "QUICK REFERENCE:\n"
    "- Volume up/down → increase_volume / decrease_volume\n"
    "- Brighter/dimmer → increase_brightness / decrease_brightness\n"
    "- WiFi on/off → toggle_wifi(True/False)\n"
    "- Weather here → get_weather_current_location()\n"
    "- World news → get_world_news()\n"
    "- Who is X → search_person(name)\n"
    "- Search hard → deep_search(query)\n"
    "- Call dad → call_contact('dad')\n"
    
    "MACROS:\n"
    "- 'morning routine / work mode / night mode / break time' → run_macro(macro_name)\n"
    "- 'create a macro called X that does Y' → create_macro(name, description, steps_json)\n"
    "- 'list my macros / what routines do I have' → list_macros()\n"
    "- 'what does work mode do' → describe_macro(macro_name)\n"
    "- 'schedule morning routine at 8am daily' → schedule_macro(macro_name, time_str, repeat)\n"
    "- 'delete gym mode macro' → delete_macro(name)\n\n"
))

def agent_node(state: AgentState):
    messages = state["messages"]
    is_admin = _is_admin_session_valid(state)

    last_human = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)),
        ""
    )

    if messages and isinstance(messages[-1], ToolMessage):
        response = llm.invoke([SYSTEM_PROMPT] + messages)
    else:
        selected_tools = get_tools_for_query(
            user_text=last_human,
            always_include=ALWAYS_TOOLS,
            is_admin=is_admin,
        )
        llm_with_tools = llm.bind_tools(selected_tools)
        response = llm_with_tools.invoke([SYSTEM_PROMPT] + messages)

    if response.tool_calls:
        logger.info(f"Tool calls: {[tc['name'] for tc in response.tool_calls]}")
    else:
        logger.info(f"Direct answer: {response.content[:80]!r}")

    return {"messages": [response]}


def tool_executor(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls   = last_message.tool_calls
    if not tool_calls:
        return {"messages": []}

    results       = []
    state_updates = {}

    for tc in tool_calls:
        tool_name = tc["name"]
        args      = tc["args"]

        if tool_name in ADMIN_TOOL_NAMES and not _is_admin_session_valid(state):
            results.append(ToolMessage(
                content="Admin access required. Calling unlock_admin to verify identity.",
                tool_call_id=tc["id"]
            ))
            continue

        try:
            if tool_name in TOOL_IMPL_MAP:
                result = TOOL_IMPL_MAP[tool_name](args, state)
            elif tool_name in ALL_TOOLS_MAP:
                result = ALL_TOOLS_MAP[tool_name].invoke(args)
            else:
                result = f"Unknown tool: {tool_name}"

            if tool_name == "unlock_admin" and result == "ADMIN_VERIFIED":
                state_updates["is_admin"] = True
                state_updates["admin_granted_at"] = time.time()
                result = "Identity verified. Admin access granted for 5 minutes."
                logger.info("Admin session started.")

            results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            logger.info(f"Tool '{tool_name}' -> {str(result)[:120]!r}")

        except Exception as e:
            logger.error(f"Tool '{tool_name}' error: {e!r}")
            results.append(ToolMessage(
                content=f"Tool error: {str(e)}", tool_call_id=tc["id"]
            ))

    update = {"messages": results}
    update.update(state_updates)
    return update


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
logger.info("agent_graph loaded: dynamic tool routing active")