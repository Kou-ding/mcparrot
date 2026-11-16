import json
import os

from mcparrot.utils.logger import my_logger

CONFIG_FILE = "static/config.json"
PLANS_DIR = "static/plans"
SESSIONS_DIR = "sessions"

_VALID_SETTINGS = {"state", "mode", "session", "servers", "stop"}
_VALID_SESSION_SETTINGS = {"stage", "report", "time"}

# Config settings
def set_setting(setting_type: str, value: str):
    if setting_type not in _VALID_SETTINGS:
        raise ValueError(f"Unknown setting: {setting_type!r}")

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)

        data[setting_type] = value

        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    else:
        raise FileNotFoundError(f"Config file missing: {CONFIG_FILE}")

def get_setting(setting_type: str):
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)

        if setting_type in _VALID_SETTINGS:
            return data[setting_type]
        if setting_type == "session_path":
            session_name = data["session"].removesuffix(".json")
            return f"plans/{session_name}_plans/info.json"
        if setting_type == "session_name":
            return data["session"].removesuffix(".json")
        else:
            raise KeyError(f"Unknown setting: {setting_type!r}")
    else:
        raise FileNotFoundError(f"Config file missing: {CONFIG_FILE}")

# Session info
def set_session_info(setting_type: str, value: str):
    if setting_type not in _VALID_SESSION_SETTINGS:
        raise ValueError(f"Unknown session setting: {setting_type!r}")

    session_name = get_setting("session_name")
    path = f"{PLANS_DIR}/{session_name}_plans/info.json"

    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)

        data[setting_type] = value

        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    else:
        raise FileNotFoundError(f"Session info file missing: {path}")

def get_session_info(setting_type: str):
    session_name = get_setting("session_name")
    path = f"{PLANS_DIR}/{session_name}_plans/info.json"

    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        if setting_type in _VALID_SESSION_SETTINGS:
            return data[setting_type]
        else:
            raise KeyError(f"Unknown session setting: {setting_type!r}")
    else:
        raise FileNotFoundError(f"Session info file missing: {path}")

# Saving and loading sessions
async def load_session(session_file):
    path = f"{SESSIONS_DIR}/{session_file}"
    try:
        with open(path, "r") as f:
            history = json.load(f)
        return history
    except FileNotFoundError:
        my_logger.error(f"Session history missing: {path}")
        return []

async def save_session(session_file, messages):
    path = f"{SESSIONS_DIR}/{session_file}"
    with open(path, "w") as f:
        json.dump(messages, f, indent=2)
