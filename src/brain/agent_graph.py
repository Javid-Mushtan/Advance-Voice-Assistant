import time
from typing import TypedDict, Annotated, Any, Optional

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool

from src.brain.memory import LongTermMemory
from src.brain.rag import conversational_rag_chain
from src.tools.system_tools import open_app, close_app, get_volume, open_website
from src.tools.api_tools import get_weather, web_search, get_weather_current_location, get_city
from src.tools.personal_tools import send_email, add_note, send_whatsapp_message, open_whatsapp_chat_for_call
from src.tools.phone_tools import (
    call_contact, call_number, end_call, resolve_contact_number,
    get_phone_last_location, get_phone_live_location,
    open_app_on_phone, set_phone_wifi, compose_sms, check_phone_connection,
)

from src.tools.system_tools import (
    toggle_wifi, scan_wifi_networks, connect_wifi,
    disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
    forget_wifi_network, get_wifi_password,
)

from src.tools.location_tools import (
    get_current_location, get_location_coordinates, get_maps_link
)

from src.tools.admin_tools import (
    scan_files, delete_file, move_file, read_file_contents, list_directory,
    uninstall_application, install_application, list_installed_apps,
    list_running_processes, kill_process, run_command,
    get_network_info, list_open_ports, ping_host,
    get_disk_usage, get_system_info, shutdown_pc, cancel_shutdown,
    restart_pc, set_volume,
)
from src.utils.config import OPENROUTER_API_KEY,HUGGING_FACE_API_TOKEN
from src.utils.logger import logger

ADMIN_SESSION_TTL = 300


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
    """Return True if admin was granted and the TTL hasn't expired."""
    if not state.get("is_admin"):
        return False
    granted_at = state.get("admin_granted_at")
    if granted_at is None:
        return False
    return (time.time() - granted_at) < ADMIN_SESSION_TTL


@tool
def rag_search(query: str) -> str:
    """Search your personal knowledge base (documents)."""
    return "Placeholder"

@tool
def remember_fact(fact: str) -> str:
    """Store a fact about the user in long-term memory."""
    return "Placeholder"

@tool
def recall_memory(query: str) -> str:
    """Retrieve facts about the user from long-term memory."""
    return "Placeholder"

@tool
def unlock_admin() -> str:
    """
    Verify the user's identity via face recognition to grant full admin access.
    MUST be called before any admin-only tool (file deletion, uninstall, shutdown, etc.).
    Only call this once per session — admin access lasts 5 minutes after verification.
    """
    return "Placeholder"


NORMAL_TOOLS = [
    rag_search, remember_fact, recall_memory,
    open_app, close_app, get_volume, open_website,
    get_weather, web_search,
    send_email, add_note, send_whatsapp_message, open_whatsapp_chat_for_call,
    call_contact, call_number, end_call, resolve_contact_number,
    get_phone_last_location, get_phone_live_location,
    open_app_on_phone, set_phone_wifi, compose_sms, check_phone_connection,
    unlock_admin,
    get_weather_current_location, get_city,
    get_current_location, get_location_coordinates, get_maps_link,
toggle_wifi, scan_wifi_networks, connect_wifi,
    disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
    forget_wifi_network, get_wifi_password
]

ADMIN_TOOLS = [
    # file system
    scan_files, delete_file, move_file, read_file_contents, list_directory,
    # software
    uninstall_application, install_application, list_installed_apps,
    # processes
    list_running_processes, kill_process, run_command,
    # network
    get_network_info, list_open_ports, ping_host,
    # system
    get_disk_usage, get_system_info, shutdown_pc, cancel_shutdown, restart_pc, set_volume,
]

ADMIN_TOOL_NAMES = {t.name for t in ADMIN_TOOLS}

ALL_TOOLS = NORMAL_TOOLS + ADMIN_TOOLS

TOOL_IMPL_MAP = {
    "rag_search":     lambda args, state: _rag_search_impl(args["query"], state["session_id"]),
    "remember_fact":  lambda args, state: _remember_fact_impl(args["fact"], state["long_term_memory"]),
    "recall_memory":  lambda args, state: _recall_memory_impl(args["query"], state["long_term_memory"]),
    "unlock_admin":   lambda args, state: _handle_unlock_admin(state),
}

def _handle_unlock_admin(state: AgentState) -> str:
    """Run face verification and return a result string. State mutation happens in tool_executor."""
    try:
        from src.utils.face_auth import verify_admin_face
        verified = verify_admin_face()
        if verified:
            return "ADMIN_VERIFIED"
        return "Face not recognised. Admin access denied."
    except ImportError:
        return "face_auth module not found. Run: pip install deepface opencv-python tf-keras"
    except Exception as e:
        return f"Face verification error: {e}"


endpoint = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-7B-Instruct",
    huggingfacehub_api_token=HUGGING_FACE_API_TOKEN
)

llm = ChatHuggingFace(llm=endpoint)

llm_with_normal_tools = llm.bind_tools(NORMAL_TOOLS)
llm_with_all_tools    = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = SystemMessage(content=(
    "You are JARVIS, a powerful personal voice assistant with full admin access to the user's laptop.\n\n"

    "ADMIN ACCESS RULES:\n"
    "- Admin-only tools (file operations, uninstall, shutdown, processes, network, etc.) require "
    "the user's identity to be verified via face recognition first.\n"
    "- If the user asks for an admin action and is_admin is False, call unlock_admin() ONCE. "
    "Do NOT explain or warn — just call it immediately.\n"
    "- If unlock_admin returns 'ADMIN_VERIFIED', proceed with the requested admin tool in the next turn.\n"
    "- If unlock returns a denial message, tell the user access was denied and stop.\n"
    "- Admin access automatically expires after 5 minutes. If it has expired and the user requests "
    "an admin action, call unlock_admin() again.\n\n"

    "MEMORY RULES:\n"
    "- If the user states a personal fact, call remember_fact to store it.\n"
    "- If the user asks something they may have told you before, call recall_memory first.\n\n"

    "GENERAL RULES:\n"
    "- The moment a tool result gives you enough information to answer, stop calling tools and respond.\n"
    "- Never call the same tool twice in a row with the same input.\n"
    "- Keep answers concise — they will be spoken aloud.\n"
    "- For destructive actions (delete, uninstall, shutdown), confirm the action with the user "
    "BEFORE executing it, e.g. 'Are you sure you want to delete test.csv?'.\n"
))


def agent_node(state: AgentState):
    messages = state["messages"]
    is_admin = _is_admin_session_valid(state)

    active_llm = llm_with_all_tools if is_admin else llm_with_normal_tools

    if messages and isinstance(messages[-1], ToolMessage):
        response = llm.invoke([SYSTEM_PROMPT] + messages)
    else:
        response = active_llm.invoke([SYSTEM_PROMPT] + messages)

    if response.tool_calls:
        logger.info(f"Tool calls: {[tc['name'] for tc in response.tool_calls]}")
    else:
        logger.info(f"Direct answer: {response.content!r}")

    return {"messages": [response]}


def tool_executor(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    if not tool_calls:
        return {"messages": []}

    results = []
    state_updates = {}

    tool_map = {t.name: t for t in ALL_TOOLS}

    for tc in tool_calls:
        tool_name = tc["name"]
        args = tc["args"]

        if tool_name in ADMIN_TOOL_NAMES and not _is_admin_session_valid(state):
            results.append(ToolMessage(
                content=(
                    "Admin access required but not verified. "
                    "I will call unlock_admin to verify your identity first."
                ),
                tool_call_id=tc["id"]
            ))
            continue

        try:
            if tool_name in TOOL_IMPL_MAP:
                result = TOOL_IMPL_MAP[tool_name](args, state)
            else:
                result = tool_map[tool_name].invoke(args)

            # Handle the admin unlock sentinel
            if tool_name == "unlock_admin" and result == "ADMIN_VERIFIED":
                state_updates["is_admin"] = True
                state_updates["admin_granted_at"] = time.time()
                result = "Identity verified. Admin access granted for 5 minutes."
                logger.info("Admin session started.")

            results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            logger.info(f"Tool '{tool_name}' -> {str(result)[:120]!r}")

        except Exception as e:
            logger.error(f"Tool '{tool_name}' error: {e!r}")
            results.append(ToolMessage(content=f"Tool error: {str(e)}", tool_call_id=tc["id"]))

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

logger.info("agent_graph loaded: admin-mode + face-unlock + TTL")