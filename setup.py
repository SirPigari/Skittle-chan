import json
import os

os.chdir(os.path.dirname(__file__))

values = {"json_files": {
            "blocked_channels.json": {"blocked_channels": []},
            "command_logs.json": [],
            "conversation_histories.json": {},
            "current_session.json": {
                "id": None,
                "pos": 0
            },
            "logged_users.json": {},
            "message_log.json": {},
            "message_logs.json": {},
            "status_messages.json": {
                "status_messages": []
            },
        },
}
IGNORE_ERRORS = False
EXIST_OK = False

def setup() -> None:
    try:
        _create_jsons()
    except Exception as e:
        if IGNORE_ERRORS:
            pass
        else:
            raise e

def config(**kwargs) -> None:
    """
    Updates the configuration settings in the `values` dictionary.

    This function allows dynamic updating of the configuration by passing
    one or more keyword arguments. Each key-value pair represents a setting
    in the `values` dictionary, where the key is the setting name, and the
    value is the new value for that setting.

    Parameters:
    -----------
    **kwargs : dict
        Keyword arguments where each key corresponds to a setting in the
        `values` dictionary, and the value represents the new setting value.

    Example Usage:
    --------------
    config(IGNORE_ERRORS=True, EXIST_OK=True)

    In this example, the `IGNORE_ERRORS` and `EXIST_OK` settings in the
    `values` dictionary will be updated to `True`.

    Description:
    ------------
    The function iterates through the provided keyword arguments and updates
    the corresponding entries in the `values` dictionary. This makes it easy
    to modify configuration settings at runtime without directly accessing
    or modifying the dictionary elsewhere in the code. This is useful for
    adjusting global behavior, such as error handling or file management
    preferences.
    """
    for kw, arg in kwargs.items():
        values[kw] = arg

def _create_jsons():
    if not os.path.exists("json/"):
        os.makedirs("json/", exist_ok=EXIST_OK)
        items = values["json_files"]
        for file, content in items.items():
            with open(f"json/{file}", 'w') as f:
                json.dump(content, f, indent=4)