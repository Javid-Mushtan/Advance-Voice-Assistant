from __future__ import annotations
import re
from typing import Any

from src.utils.logger import logger

from src.tools.system_tools import (
    open_app, close_app, get_volume, open_website,
    toggle_wifi, scan_wifi_networks, connect_wifi,
    disconnect_wifi, get_wifi_status, list_saved_wifi_networks,
    forget_wifi_network, get_wifi_password,
    set_volume, get_current_volume, increase_volume, decrease_volume,
    mute_volume, unmute_volume,
    set_brightness, get_brightness, increase_brightness, decrease_brightness,
    turn_on_bluetooth, turn_off_bluetooth, toggle_airplane_mode,
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
from src.tools.news_search_tools import (
    get_world_news, get_news_by_topic, deep_search, search_person,
)

TOOL_GROUPS: dict[str, list] = {

    "app_control": [
        open_app, close_app, open_website,
    ],

    "volume": [
        set_volume, get_current_volume,
        increase_volume, decrease_volume,
        mute_volume, unmute_volume,
    ],

    "brightness": [
        set_brightness, get_brightness,
        increase_brightness, decrease_brightness,
    ],

    "wifi": [
        toggle_wifi, scan_wifi_networks, connect_wifi,
        disconnect_wifi, get_wifi_status,
        list_saved_wifi_networks, forget_wifi_network, get_wifi_password,
    ],

    "bluetooth": [
        turn_on_bluetooth, turn_off_bluetooth,
    ],

    "system_settings": [
        get_volume, set_volume, get_current_volume,
        increase_volume, decrease_volume, mute_volume, unmute_volume,
        set_brightness, get_brightness, increase_brightness, decrease_brightness,
        toggle_airplane_mode, turn_on_bluetooth, turn_off_bluetooth,
    ],

    "weather": [
        get_weather, get_weather_current_location, get_city,
        get_current_location,
    ],

    "location": [
        get_current_location, get_location_coordinates,
        get_maps_link, get_city,
    ],

    "news": [
        get_world_news, get_news_by_topic,
    ],

    "search": [
        web_search, deep_search, search_person,
    ],

    "messaging": [
        send_email, add_note,
        send_whatsapp_message, open_whatsapp_chat_for_call,
    ],

    "phone_calls": [
        call_contact, call_number, end_call,
        resolve_contact_number, check_phone_connection,
    ],

    "phone_control": [
        open_app_on_phone, set_phone_wifi, compose_sms,
        get_phone_last_location, get_phone_live_location,
        check_phone_connection,
    ],

    "file_system": [
        scan_files, delete_file, move_file,
        read_file_contents, list_directory,
    ],

    "software": [
        uninstall_application, install_application, list_installed_apps,
    ],

    "processes": [
        list_running_processes, kill_process, run_command,
    ],

    "network_admin": [
        get_network_info, list_open_ports, ping_host, run_command,
    ],

    "system_power": [
        get_disk_usage, get_system_info,
        shutdown_pc, cancel_shutdown, restart_pc,
    ],
}

ALWAYS_INCLUDE: list = []

INTENT_RULES: list[tuple[int, list[str], list[str]]] = [

    (10, [r"\bopen\b", r"\blaunch\b", r"\bstart\b"], ["app_control"]),
    (10, [r"\bclose\b", r"\bkill app\b", r"\bquit\b"], ["app_control"]),
    (10, [r"\bwebsite\b", r"\burl\b", r"\.com\b", r"\.lk\b",
          r"\bgo to\b", r"\bbrowse\b"], ["app_control"]),

    (10, [r"\bvolume\b", r"\blouder\b", r"\bquieter\b",
          r"\bmute\b", r"\bunmute\b", r"\bsound\b"], ["volume"]),

    (10, [r"\bbrightness\b", r"\bbrighter\b", r"\bdimmer\b",
          r"\bscreen light\b", r"\bdark(er)?\b"], ["brightness"]),

    (10, [r"\bwi.?fi\b", r"\bwireless\b", r"\bhotspot\b",
          r"\bconnect to\b", r"\bnetwork password\b"], ["wifi"]),

    (10, [r"\bbluetooth\b", r"\bbt\b"], ["bluetooth"]),

    (10, [r"\bairplane\b", r"\bflight mode\b"], ["system_settings"]),

    (10, [r"\bweather\b", r"\btemperature\b", r"\brain\b",
          r"\bsunny\b", r"\bhumid\b", r"\bforecast\b",
          r"\bclimate\b"], ["weather"]),

    (10, [r"\blocation\b", r"\bwhere am i\b", r"\bmy location\b",
          r"\bmap\b", r"\bgps\b", r"\bcoordinates\b",
          r"\baddress\b", r"\bnavigat\b"], ["location"]),

    (10, [r"\bnews\b", r"\bheadlines?\b", r"\bcurrent events?\b",
          r"\bwhat.?s happening\b", r"\btoday.?s news\b"], ["news"]),

    (10, [r"\bsearch hard\b", r"\badvanced search\b", r"\bdig deep\b",
          r"\bresearch\b", r"\bfind (everything|all|details)\b",
          r"\btell me (everything|all) about\b"], ["search"]),

    (10, [r"\bwho is\b", r"\bwho was\b", r"\btell me about\b",
          r"\bbiograph\b"], ["search"]),

    (5, [r"\bsearch\b", r"\blook up\b", r"\bfind out\b",
         r"\bwhat is\b", r"\bwhat are\b", r"\bhow (to|do|does)\b",
         r"\bwhen (was|did|is)\b"], ["search"]),

    (10, [r"\bemail\b", r"\bsend (a )?message\b", r"\bwhatsapp\b",
          r"\bnote\b", r"\breminder\b"], ["messaging"]),

    (10, [r"\bcall\b", r"\bdial\b", r"\bphone (call|number)\b",
          r"\bring\b", r"\bhang up\b", r"\bend call\b"], ["phone_calls"]),

    (10, [r"\btext\b", r"\bsms\b", r"\bsend (a )?text\b",
          r"\bmessage (to )?\w+\b"], ["phone_control"]),

    (10, [r"\bphone\b.*\bopen\b", r"\bopen.*on (my )?phone\b",
          r"\bphone.?wifi\b", r"\bphone.?location\b",
          r"\bwhere.?is.?my phone\b"], ["phone_control"]),

    (10, [r"\bfind (file|folder)\b", r"\bscan.*file\b",
          r"\bdelete (file|folder)\b", r"\bmove file\b",
          r"\bread file\b", r"\blist (files|directory)\b",
          r"\b\.csv\b", r"\b\.txt\b", r"\b\.pdf\b",
          r"\b\.docx?\b", r"\b\.xlsx?\b"], ["file_system"]),

    (10, [r"\binstall\b", r"\buninstall\b", r"\bremove (app|application|software)\b",
          r"\blist (apps|installed)\b"], ["software"]),

    (10, [r"\bprocess(es)?\b", r"\btask manager\b", r"\brunning apps\b",
          r"\bkill process\b", r"\bforce (stop|quit|close)\b",
          r"\brun command\b", r"\bterminal command\b"], ["processes"]),

    (10, [r"\bopen port\b", r"\bnetstat\b", r"\bping\b",
          r"\bip (address|config)\b", r"\bipconfig\b",
          r"\bnetwork (info|details|adapter)\b"], ["network_admin"]),

    (10, [r"\bshutdown\b", r"\brestart\b", r"\bshut down\b",
          r"\breboot\b", r"\bdisk (usage|space)\b",
          r"\bsystem info\b", r"\bram\b", r"\bstorage\b",
          r"\bcancel shutdown\b"], ["system_power"]),
]

def get_tools_for_query(
    user_text: str,
    always_include: list,
    is_admin: bool = False,
) -> list:

    text = user_text.lower().strip()

    matched_groups: list[str] = []

    for priority, patterns, groups in INTENT_RULES:
        if any(re.search(p, text) for p in patterns):
            matched_groups.extend(groups)

    seen_groups = []
    for g in matched_groups:
        if g not in seen_groups:
            seen_groups.append(g)

    ADMIN_GROUPS = {"file_system", "software", "processes", "network_admin", "system_power"}
    if not is_admin:
        seen_groups = [g for g in seen_groups if g not in ADMIN_GROUPS]

    selected_tools: list = list(always_include)
    seen_names = {t.name for t in selected_tools}

    for group in seen_groups:
        for t in TOOL_GROUPS.get(group, []):
            if t.name not in seen_names:
                selected_tools.append(t)
                seen_names.add(t.name)

    if len(selected_tools) == len(always_include):
        fallback = [web_search]
        for t in fallback:
            if t.name not in seen_names:
                selected_tools.append(t)
        logger.info(f"[Router] No specific match — fallback to minimal tools")

    else:
        logger.info(
            f"[Router] Intent groups: {seen_groups} → "
            f"{len(selected_tools)} tools selected"
        )

    return selected_tools

#for debug purpose javid
def describe_routing(user_text: str, tools: list) -> None:
    names = [t.name for t in tools]
    logger.debug(f"[Router] Query: {user_text!r}")
    logger.debug(f"[Router] Selected tools ({len(names)}): {names}")