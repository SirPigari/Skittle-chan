Skittle-chan Discord Bot
========================

A fun and interactive Discord bot for your servers! Follow the instructions below to set it up and start using it.

* * *

📥 Getting Started
------------------

### 1\. Clone the Bot Files

Clone the repository containing the bot files and save them to a directory on your local machine.

Cd to directory where you want to create the skittle-chan (eg.: `C:/Documents`)

```BATCH
:: Navigate to the directory where you want to clone the repository
cd "C:\Documents"

:: Create the directory
mkdir "skittle-chan"

:: Clone the repository into a directory named 'skittle-chan'
git clone "https://github.com/SirPigari/Skittle-chan/" "skittle-chan"

:: Navigate into the cloned repository
cd "skittle-chan"
```


* * *

🛠 Prerequisites
----------------

### 2\. Install Python

*   **Required Version:** Python 3.12
*   Download Python 3.12 from the official Python website: [https://www.python.org/downloads/](https://www.python.org/downloads/)
*   Make sure to check the box for **"Add Python to PATH"** during installation.

### 3\. Install Required Libraries

Run the following command in your terminal to install all the necessary Python libraries:

To install all the necessary Python libraries, follow these steps:

1.  Ensure you have a `requirements.txt` file.

3.  Run the following command in your terminal:

    ```BATCH
    pip install -r requirements.txt
    ```

This will automatically install all required libraries listed in the `requirements.txt` file.

* * *

📋 Setup
--------

### 4\. Create `variables.py`

1.  Edit the `variables.py` file in the directory.
2.  Paste the following template into it:

```PYTHON
import discord
import platform

_os_name = platform.system()
_os_version = platform.version()

VERSION: str = "1.7"
__VERSION__: str = "1.7"
CHATGPT_VERSION: str = "ChatGPT-4o"
DISCORD_BOT_TOKEN: str = 'YOUR_DISCORD_BOT_TOKEN'
CLIENT_ID: str = 'YOUR_CLIENT_ID'
SKITTLE_CHAN_ID: str = 'YOUR_BOT_ID'
COLOR_MAP: dict = {
    "blue": discord.Color.blue(),
    "red": discord.Color.red(),
    "green": discord.Color.green(),
    "yellow": discord.Color.yellow(),
    "purple": discord.Color.purple(),
    "orange": discord.Color.orange(),
    "black": discord.Color.from_rgb(0, 0, 0),
    "white": discord.Color.from_rgb(255, 255, 255),
    "grey": discord.Color.from_rgb(128, 128, 128),
    "pink": discord.Color.from_rgb(255, 192, 203),
    "magenta": discord.Color.from_rgb(255, 0, 255),
    "blurple": discord.Color.blurple()
}
RPC_JOIN: str = 'YOUR_RPC_JOIN_TOKEN'
PARTY_ID: str = 'YOUR_PARTY_ID'
SENDER_EMAIL: str = "YOUR_EMAIL@gmail.com"
SENDER_PASSWORD: str = "YOUR_EMAIL_PASSWORD"
RECEIVER_EMAIL: str = "TARGET_EMAIL@gmail.com"
DOC_LINK: str = "YOUR_DOC_LINK"
CURRENT_OS: str = f"{_os_name}: {_os_version}"
MAIN_SERVER_ID: int = YOUR_MAIN_SERVER_ID
SERVER_INVITE: str = "YOUR_INVITE_CODE"
ADMIN_ROLE_ID: int = YOUR_ADMIN_ROLE_ID
MOD_ROLE_ID: int = YOUR_MOD_ROLE_ID
TICKET_CHANNEL_ID: int = YOUR_TICKET_CHANNEL_ID
TICKET_MESSAGE_ID: int = YOUR_TICKET_MESSAGE_ID
```

**Note 1:** Replace all placeholders (e.g., `YOUR_DISCORD_BOT_TOKEN`) with the appropriate values.

**Note 2:** Constants `SENDER_EMAIL`, `SENDER_PASSWORD` and `RECIEVER_EMAIL` are only used for one command and aren't required.

* * *

▶️ Running the Bot
------------------

### 5\. Start the Bot

1.  Open your terminal and navigate to the directory containing the bot files.
2.  Run the following command to start the bot:

    ```BATCH
    python main.py
    ```

* * *

🎉 Features
-----------

*   Customizable colors
*   User-friendly ticketing system
*   Integration with multiple roles and channels
*   And much more!

* * *

📚 Documentation
----------------

Documentation link: _Coming Soon!_

* * *

🤝 Support
----------

If you encounter issues or need help, reach out via email: [skittlechan.help@gmail.com](mailto:skittlechan.help@gmail.com)

* * *

Made with ❤️ by the Skittle-chan Team
