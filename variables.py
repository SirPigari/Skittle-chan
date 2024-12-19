import os
from datetime import datetime
os.chdir(os.path.dirname(__file__))

VERSION = None
__VERSION__ = None
CHATGPT_VERSION = None
DISCORD_BOT_TOKEN = None
CLIENT_ID = None
SKITTLE_CHAN_ID = None
COLOR_MAP = {}
RPC_JOIN = None
PARTY_ID = None
SENDER_EMAIL = None
SENDER_PASSWORD = None
RECEIVER_EMAIL = None
DOC_LINK = None
CURRENT_OS = None
MAIN_SERVER_ID = None
SERVER_INVITE = None
ADMIN_ROLE_ID = None
MOD_ROLE_ID = None
TICKET_CHANNEL_ID = None
TICKET_MESSAGE_ID = None
MEMBER_ROLE_ID = None

path = "A:/variables.py"

def read_and_execute(file_path):
    try:
        with open(file_path, "r") as f:
            code = f.read()
        exec(code, globals())
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [system-0000000000000000000] (⚙️|SYSTEM): Failed to execute the file. Error: {e}")
        return False
    return True

if os.path.exists(path):
    with open(path, "r") as f:
        with open("other/vars.py", "w") as fr:
            fr.write(f.read())
    read_and_execute(path)
else:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [system-0000000000000000000] (⚙️|SYSTEM): File '{path}' not found. Enter a valid path or press enter to exit.")
    while True:
        user_input = input(">> ")
        if not user_input:
            raise FileNotFoundError(f"File '{path}' was not found, and no valid input was provided.")
        elif os.path.exists(user_input):
            if read_and_execute(user_input):
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [system-0000000000000000000] (⚙️|SYSTEM): Executed file at '{user_input}'.")
                break
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [system-0000000000000000000] (⚙️|SYSTEM): Path '{user_input}' is not valid. Please try again.")
