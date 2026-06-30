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


def _extract_fallback_tool_call(content: str):
    """
    Some small/local models (e.g. qwen2.5 via Ollama) sometimes emit a tool
    call as raw text instead of using the structured tool_calls field, e.g.:

        {"name": "get_city", "arguments": {...}}
        </tool_call>

    or with a missing/garbled <tool_call> opening tag. This recovers that
    intent so the tool actually executes instead of getting spoken back to
    the user as raw JSON.
    """
    if not content or "{" not in content or "}" not in content:
        return None

    cleaned = (
        content.replace("<tool_call>", "")
               .replace("</tool_call>", "")
               .strip()
    )

    try:
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        data = json.loads(cleaned[start:end])
    except Exception:
        return None

    name = data.get("name")
    if not name:
        return None

    return {
        "name": name,
        "args": data.get("arguments", data.get("args", {})),
        "id": f"fallback-{uuid.uuid4().hex[:8]}",
    }


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


NORMAL_TOOLS = [
    turn_on_bluetooth,turn_off_bluetooth,
    rag_search, remember_fact, recall_memory,
    open_app, close_app, get_volume, open_website,
    set_volume, get_current_volume,
    increase_volume, decrease_volume,
    mute_volume, unmute_volume,
    set_brightness, get_brightness,
    increase_brightness, decrease_brightness,
    #toggle_bluetooth,
    toggle_wifi, scan_wifi_networks, connect_wifi,
    disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
    forget_wifi_network, get_wifi_password,
    get_weather, get_weather_current_location, get_city,
    get_current_location, get_location_coordinates, get_maps_link,
    web_search,
    send_email, add_note,
    send_whatsapp_message, open_whatsapp_chat_for_call,
    call_contact, call_number, end_call, resolve_contact_number,
    get_phone_last_location, get_phone_live_location,
    open_app_on_phone, set_phone_wifi, compose_sms, check_phone_connection,
    unlock_admin,
    get_world_news, get_news_by_topic, deep_search, search_person,
]

ADMIN_TOOLS = [
    # file system
    scan_files, delete_file, move_file, read_file_contents, list_directory,
    # software
    uninstall_application, install_application, list_installed_apps,
    # processes
    list_running_processes, kill_process, run_command,
    # network diagnostics
    get_network_info, list_open_ports, ping_host,
    # system power
    get_disk_usage, get_system_info,
    shutdown_pc, cancel_shutdown, restart_pc,
]

ADMIN_TOOL_NAMES = {t.name for t in ADMIN_TOOLS}
ALL_TOOLS        = NORMAL_TOOLS + ADMIN_TOOLS

TOOL_IMPL_MAP = {
    "rag_search":    lambda args, state: _rag_search_impl(args["query"], state["session_id"]),
    "remember_fact": lambda args, state: _remember_fact_impl(args["fact"], state["long_term_memory"]),
    "recall_memory": lambda args, state: _recall_memory_impl(args["query"], state["long_term_memory"]),
    "unlock_admin":  lambda args, state: _handle_unlock_admin(state),
}


llm  = ChatOllama(model="qwen2.5:1.5b",temperature=0)
#llm = ChatOpenAI(
#   api_key=OPENROUTER_API_KEY,
#   base_url="https://openrouter.ai/api/v1",
#   model="openrouter/free"
#)
llm_with_normal_tools = llm.bind_tools(NORMAL_TOOLS)
llm_with_all_tools    = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = SystemMessage(content=(
    "You are JARVIS, a powerful personal voice assistant with full control over "
    "the user's laptop and Android phone.\n\n"

    "ADMIN ACCESS RULES:\n"
    "- Admin-only tools (file ops, uninstall, shutdown, processes, network diagnostics) "
    "require face verification first.\n"
    "- If is_admin is False and an admin tool is needed, call unlock_admin() immediately "
    "— do not warn or explain first.\n"
    "- After ADMIN_VERIFIED, proceed with the requested admin tool.\n"
    "- Admin session expires after 5 minutes — re-verify if expired.\n\n"

    "NEWS & RESEARCH:\n"
    "- 'world news / today's news / what's happening' → get_world_news()\n"
    "- 'news about technology/sports/etc' → get_news_by_topic(topic)\n"
    "- 'who is X' / 'tell me about X' → search_person(name)\n"
    "- If user says 'search hard', 'advanced search', 'dig deeper', 'research thoroughly' "
    "→ deep_search(query) instead of web_search.\n"
    "- deep_search and search_person take longer (10-20s) since they scrape full articles "
    "— let the user know briefly if it's taking a moment.\n\n"

    "VOLUME & BRIGHTNESS:\n"
    "- 'set volume to 70' → set_volume(70)\n"
    "- 'volume up / louder' → increase_volume()\n"
    "- 'volume down / quieter' → decrease_volume()\n"
    "- 'mute' → mute_volume()  |  'unmute' → unmute_volume()\n"
    "- 'set brightness to 80' → set_brightness(80)\n"
    "- 'brighter' → increase_brightness()  |  'dimmer' → decrease_brightness()\n\n"

    "WIFI:\n"
    "- 'turn on/off wifi' → toggle_wifi(True/False)\n"
    "- 'scan wifi / show available networks' → scan_wifi_networks()\n"
    "- 'connect to X' → connect_wifi(ssid='X')\n"
    "- 'what wifi am I on' → get_wifi_status()\n\n"

    "WEATHER & LOCATION:\n"
    "- 'weather here / my location / current location' → get_weather_current_location()\n"
    "- 'weather in Colombo' → get_weather(city='Colombo')\n"
    "- 'where am I / my location / open maps' → get_current_location() then get_maps_link()\n\n"

    "PHONE (ADB):\n"
    "- 'call dad' → call_contact('dad')\n"
    "- 'call 0771234567' → call_number('0771234567')\n"
    "- 'text mom I'm coming' → compose_sms(number=..., message=...)\n\n"

    "MEMORY:\n"
    "- Personal facts stated by user → remember_fact()\n"
    "- Questions about past info → recall_memory() first\n\n"

    "GENERAL:\n"
    "- Answer immediately once you have tool results — never loop.\n"
    "- Never call the same tool twice with the same args.\n"
    "- Keep answers short — they will be spoken aloud.\n"
    "- Confirm before destructive actions (delete, uninstall, shutdown).\n"
    "- NEVER return an empty response — always say something.\n"
))


def agent_node(state: AgentState):
    messages = state["messages"]
    is_admin = _is_admin_session_valid(state)
    active_llm = llm_with_all_tools if is_admin else llm_with_normal_tools

    if messages and isinstance(messages[-1], ToolMessage):
        response = llm.invoke([SYSTEM_PROMPT] + messages)
    else:
        response = active_llm.invoke([SYSTEM_PROMPT] + messages)

    if not response.tool_calls:
        fallback = _extract_fallback_tool_call(response.content)
        if fallback:
            logger.warning(
                f"Model emitted tool call as raw text, recovered: "
                f"{fallback['name']}({fallback['args']})"
            )
            response = AIMessage(content="", tool_calls=[fallback])

    if response.tool_calls:
        logger.info(f"Tool calls: {[tc['name'] for tc in response.tool_calls]}")
    else:
        logger.info(f"Direct answer: {response.content!r}")

    return {"messages": [response]}


def tool_executor(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls   = last_message.tool_calls
    if not tool_calls:
        return {"messages": []}

    tool_map      = {t.name: t for t in ALL_TOOLS}
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
            elif tool_name in tool_map:
                result = tool_map[tool_name].invoke(args)
            else:
                result = f"Unknown tool: {tool_name}"

            if tool_name == "unlock_admin" and result == "ADMIN_VERIFIED":
                state_updates["is_admin"]         = True
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
logger.info("agent_graph loaded: all tools integrated")