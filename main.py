import asyncio
import sys
import discord
import pypresence.exceptions
from discord.ext import commands, tasks
from discord.ui import View, Button, select, Select, button, TextInput
from datetime import datetime, timedelta
import tasks
from discord import app_commands, ButtonStyle, Interaction, Embed, SelectOption
import random
import subprocess
import variables  # Constants
import os
import json
import time
from datetime import datetime
from pypresence import AioPresence
import bot as ai
from discord import PermissionOverwrite
import re
import atexit
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import warnings
import traceback
import setup

# You can edit this config to whatever you want.
setup.config()

# Setup
setup.setup()

os.chdir(os.path.dirname(__file__))

# Ignore the EventLoop errors.
warnings.simplefilter("ignore", RuntimeWarning)
warnings.simplefilter("ignore", UserWarning)

asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# I don't actually know what the fuck does this do
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Stupid
sir_pigari_mention = "<@1009586717315059793>"
allowed_ids = frozenset(("1009586717315059793", "1212802972736557106", "952585562001387560", "1089232807047467088",))
underage_ids = frozenset(("332603062835347467",))
blocked_ids = frozenset(())
sir_pigari_id = "1009586717315059793"

TICKET_CHANNEL_ID = variables.TICKET_CHANNEL_ID
TICKET_MESSAGE_ID = variables.TICKET_MESSAGE_ID
TICKET_CATEGORIES = ["Login Issue", "Request My Personal Data", "Request Data Deletion", "Appeal Skittle-chan Ban", "Source Code Request", "Dev Team Application", "Mod Role Request",  "Other", "test"]

protected_fields = frozenset({"username", "userid", "date_logged", "perm_lvl", "email"})

def load_blocked_channels(file_path='json/blocked_channels.json'):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            data = {"blocked_channels": []}
        return set(data.get("blocked_channels", []))
    return set()

def save_blocked_channels(blocked_channels, file_path='json/blocked_channels.json'):
    with open(file_path, 'w') as f:
        json.dump({'blocked_channels': list(blocked_channels)}, f)

blocked_channels = load_blocked_channels()
save_blocked_channels(blocked_channels)

try:
    with open("json/logged_users.json", "r") as f:
        logged_users = json.load(f)
except FileNotFoundError:
    logged_users = {}

def update_session(file_path='./json/current_session.json'):
    global session_id, session_pos
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({"id": session_id, "pos": 0}, f)
        log_system_info(None, "Initialized 'json/current_session.json' with default values.")
        return

    # Read the current data from the file
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Increment the session position
    current_pos = data.get('pos', 0)
    new_pos = current_pos + 1

    # Update the data with the new session position
    data['pos'] = new_pos
    data["id"] = session_id

    # Write the updated data back to the file
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

    session_pos = new_pos

def check_if_channel_blocked():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            if interaction.channel.id in blocked_channels:
                await interaction.response.send_message(
                    "This channel is blocked for bot commands.",
                    ephemeral=True
                )
                return False
            return True
        except discord.app_commands.errors.CheckFailure:
            pass
        except Exception as e:
            log_system_info(None, e)
        return False

    return app_commands.check(predicate)


def is_logged_in():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            # Check if user is logged in
            if str(interaction.user.id) not in logged_users.keys():
                await interaction.response.send_message(
                    "You need to be logged in to use this command. Use /login to log in to Skittle-chan.",
                    ephemeral=True
                )
            return True
        except discord.app_commands.errors.CheckFailure as check_failure_error:
            log_command(interaction, interaction.command.name, interaction.data.get('options', []))
        except Exception as e:
            log_system_info(None, e)
        return False

    return app_commands.check(predicate)


def is_admin_or_dm():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            if interaction.guild is None or interaction.user.guild_permissions.administrator:
                return True

            await interaction.response.send_message(
                "You need to have admin privileges to use this command.",
                ephemeral=True
            )
        except discord.app_commands.errors.CheckFailure:
            pass
        except Exception as e:
            log_system_info(None, e)
        return False

    return app_commands.check(predicate)


def check_guild():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            if interaction.guild is None:
                return True

            guild = interaction.guild
            bot_in_guild = any(member.id == interaction.client.user.id for member in guild.members)
            if bot_in_guild:
                return True

            if not guild.verification_level >= discord.VerificationLevel.high:
                await interaction.response.send_message(
                    "The bot is not in this server, and external apps are disabled.",
                    ephemeral=True
                )
                return False
        except discord.app_commands.errors.CheckFailure:
            pass
        except Exception as e:
            log_system_info(None, f"Error: {e}")
        return False

    return app_commands.check(predicate)


# Had to implement it
def nsfw_or_dm_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            if isinstance(interaction.channel, discord.DMChannel):
                return True

            if isinstance(interaction.channel, discord.TextChannel) and interaction.channel.is_nsfw():
                return True

            await interaction.response.send_message(
                "This command can only be used in age-restricted channels or in DMs.",
                ephemeral=True
            )
        except discord.app_commands.errors.CheckFailure:
            pass
        except Exception as e:
            log_system_info(None, e)
        return False

    return app_commands.check(predicate)


def is_channel_blocked(interaction: discord.Interaction) -> bool:
    return interaction.channel.id in blocked_channels

session_pos = 1
session_id = None

error_occurred = False
verification_code = None
error_message = ""

client_id = variables.CLIENT_ID
rpc = AioPresence(client_id)

bot_client_id = variables.SKITTLE_CHAN_ID
brpc = AioPresence(bot_client_id)

verification_codes = {}

message_log = {}

async def update_bot_presence():
    await brpc.connect()

    await brpc.update(
        state="Watching anime",
        details="To Love Ru Darkness - ep12",
        start=time.time(),
        end=time.time() + 14000,
        large_image="dfs",  # Replace with actual image key from Discord Developer Portal
        large_text="*blushes*",  # Tooltip for the large image
        party_id=variables.PARTY_ID,  # Party ID
        party_size=[1, 69],  # [Current party size, Max party size]
        join=variables.RPC_JOIN  # Join secret
    )

async def update_presence():
    # Connect to Discord
    await rpc.connect()

    # Update the Rich Presence
    await rpc.update(
        state="Watching anime",
        details="To Love Ru Darkness - ep12",
        start=time.time(),
        end=time.time() + 14000,
        large_image="dfs",  # Replace with actual image key from Discord Developer Portal
        large_text="*blushes*",  # Tooltip for the large image
        party_id=variables.PARTY_ID,  # Party ID
        party_size=[1, 69],  # [Current party size, Max party size]
        join=variables.RPC_JOIN  # Join secret
    )

    # Keep the connection alive and update periodically
    while True:
        await asyncio.sleep(15)  # Update every 15 seconds as required by Discord


def log_message(message, c=None):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = message.author.name
        user_id = message.author.id
        if isinstance(message.channel, discord.DMChannel):
            channel_name = "DM with " + message.author.name
        else:
            channel_name = message.channel.name
        if message.attachments:
            content = message.attachments[0].url
        else:
            content = c if c else message.content

        content = content.replace("\n", "\033[0;37m\\n\033[0m")

        channel_id = str(message.channel.id)

        log_entry = f"[{timestamp}] [{username}-{user_id}] ({channel_name}): {content}"

        if channel_id not in message_log:
            message_log[channel_id] = []
        message_log[channel_id].append(log_entry)

        with open("json/message_log.json", "w") as f:
            json.dump(message_log, f, indent=4)

        print(log_entry)
    except Exception as e:
        log_system_info(None, e)


async def _run_script(python, script):
    await on_shutdown()
    os.system(f"{python} {script}")

async def run_script(python, script):
    await _run_script(python, script)

def log_bot_info(message, c=None):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = bot.user.name
        user_id = bot.user.id
        content = c if (c is not None) else message.content
        if isinstance(message.channel, discord.DMChannel):
            channel_name = "DM with " + message.author.name
        else:
            channel_name = message.channel.name

        content = content.replace("\n", "\033[0;37m\\n\033[0m")

        log_entry = f"[{timestamp}] [{username}-{user_id}] ({channel_name}): {content}"

        if channel_id not in message_log:
            message_log[channel_id] = []
        message_log[channel_id].append(log_entry)

        with open("json/message_log.json", "w") as f:
            json.dump(message_log, f, indent=4)

        print(log_entry)
    except Exception as e:
        pass

def log_system_info(message=None, c=None):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = "system"
        user_id = "0000000000000000000"
        channel_name = "⚙️|SYSTEM"
        channel_id = "0000000000000000000"
        content = c if c else message.content
        content = content.replace("\n", "\033[0;37m\\n\033[0m")
        log_entry = f"[{timestamp}] [{username}-{user_id}] ({channel_name}): {content}"

        if channel_id not in message_log:
            message_log[channel_id] = []
        message_log[channel_id].append(log_entry)

        with open("json/message_log.json", "w") as f:
            json.dump(message_log, f, indent=4)

        print(log_entry)
    except Exception as e:
        print(f"[{timestamp}] [{username}-{user_id}] ({channel_name}): {e}")


def log_command(interaction, command_name, *args, past=False):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        username = interaction.user.name  # Get username
        user_id = interaction.user.id  # Get user ID
        channel_id = interaction.channel.id
        if not past:
            command = f'/{command_name} {" ".join(str(arg) for arg in args)}'
        else:
            command = f'/{command_name} {" ".join(str(arg) for arg in args)} (past)'

        # Check if the interaction is in a DM or a guild channel
        if isinstance(interaction.channel, discord.DMChannel):
            channel_name = f"DM with {username}"
        else:
            channel_name = interaction.channel.name

        log_entry = {
            'timestamp': timestamp,
            'username': username,
            'user_id': user_id,
            'channel_name': channel_name,
            'command': command
        }

        # Check if command_logs.json exists and load it
        if os.path.exists('json/command_logs.json'):
            with open('json/command_logs.json', 'r', encoding='utf-8') as log_file:
                try:
                    logs = json.load(log_file)  # Load existing logs
                    if not isinstance(logs, list):  # Ensure it's a list
                        logs = []
                except json.JSONDecodeError:
                    logs = []  # File exists but is empty or contains invalid JSON
        else:
            logs = []  # Initialize an empty list if the file does not exist

        # Append the new log entry to the list
        logs.append(log_entry)

        # Write the updated list of logs back to the file
        with open('json/command_logs.json', 'w', encoding='utf-8') as log_file:
            json.dump(logs, log_file, indent=4)  # Pretty-print with indentation

        command = command.replace("\n", "\033[0;37m\\n\033[0m")
        log_entry = f"[{timestamp}] [{username}-{user_id}] ({channel_name}): {command}"

        if channel_id not in message_log:
            message_log[channel_id] = []
        message_log[channel_id].append(log_entry)

        with open("json/message_log.json", "w") as f:
            json.dump(message_log, f, indent=4)

        print(log_entry)
    except Exception as e:
        print(f'Error logging command: {e}')


def chunk_string(input_string, chunk_size=1000):
    if len(input_string) < 1000:
        return [input_string]
    # Ensure that input_string is indeed a string
    if not isinstance(input_string, str):
        raise ValueError("Input must be a string.")

    # Split the string into chunks of the specified size (default is 1000)
    return [input_string[i:i + chunk_size] for i in range(0, len(input_string), chunk_size)]

def get_perm_lvl(user_id) -> list[str, str]:
    user_id = str(user_id)
    if user_id == sir_pigari_id:
        return ["4", "4 (owner)"]
    elif user_id in blocked_ids:
        return ["0", "0 (blocked)"]
    elif user_id in allowed_ids and user_id in underage_ids:
        return ["2", "2 (normal)"]
    elif user_id in allowed_ids:
        return ["3", "3 (admin)"]
    elif user_id in underage_ids:
        return ["1", "1 (low)"]
    else:
        return ["2", "2 (normal)"]

def load_status_messages():
    try:
        with open("json/status_messages.json", "r") as f:
            data = json.load(f)
            # Check if the loaded data is structured as expected
            if not isinstance(data, dict) or "status_messages" not in data:
                raise ValueError("Invalid data format: Missing 'status_messages' key.")
            return data
    except FileNotFoundError:
        # If the file doesn't exist, return an empty structure
        return {"status_messages": []}
    except json.JSONDecodeError:
        # Handle JSON decode errors, which may occur if the file is not valid JSON
        log_system_info(None, "Failed to decode JSON. Returning empty status messages.")
        return {"status_messages": []}
    except ValueError as ve:
        # Handle any ValueErrors raised from our checks
        log_system_info(None, f"ValueError: {ve}")
        return {"status_messages": []}

async def recreate_status_messages(bot):
    # Load status messages from JSON
    status_messages = load_status_messages()

    # Iterate over each dictionary entry in the list
    for entry in status_messages:
        # Check if entry is actually a dictionary to avoid unexpected errors
        if isinstance(entry, dict):
            channel_id = int(entry.get("channel_id"))
            is_dm = entry.get("is_dm", False)
            user_id = entry.get("user_id") if is_dm else None

            if is_dm:
                # Fetch the DM channel for the user
                user = await bot.fetch_user(user_id)
                channel = user.dm_channel or await user.create_dm()
            else:
                # Get the guild channel directly
                channel = bot.get_channel(channel_id)

            # Proceed only if channel exists
            if channel:
                try:
                    # Re-create the message in the respective channel
                    message_id = int(entry.get("message_id"))
                    message = await channel.fetch_message(message_id)

                    # Update with new status, assuming a function to edit or update exists
                    await status_message_update(message, status="Offline")  # Update message as needed
                except Exception as e:
                    log_system_info(None, f"Failed to update message in channel {channel_id}: {e}")


async def sign_up_user(bot, interaction, email):
    await interaction.response.defer(ephemeral=True)

    user_id = interaction.user.id
    verification_code = str(random.randint(100000, 999999))

    # Store the code for the user in a dictionary
    verification_codes[user_id] = verification_code

    # Extract information from the interaction
    user_name = interaction.user.name

    # Get current time and date
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Construct the email with HTML for professional formatting
    email_body = f"""
    <html>
        <body>
            <h2 style="color: #333;">Welcome to Skittle-chan Verification</h2>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>Thank you for signing up! To verify your email address, please use the following code:</p>
            <h3 style="background-color: #f2f2f2; padding: 10px; text-align: center; border: 1px solid #ddd;">
                {verification_code}
            </h3>
            <p>This code is valid for a limited time. Please do not share it with anyone else.</p>
            <hr>
            <h4>Your Information</h4>
            <p><strong>User ID:</strong> {user_id}</p>
            <p><strong>Request Time:</strong> {current_time}</p>
            <br>
            <p style="color: #777;">If you did not initiate this request, please ignore this email or contact our support team.</p>
            <p>Best regards,<br>Skittle-chan Support Team</p>
        </body>
    </html>
    """

    # Prepare the email message with HTML content
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Skittle-chan Email Verification Code"
    msg["From"] = variables.SENDER_EMAIL
    msg["To"] = email
    msg.attach(MIMEText(email_body, "html"))

    # Send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(variables.SENDER_EMAIL, variables.SENDER_PASSWORD)
            server.sendmail(variables.SENDER_EMAIL, email, msg.as_string())
        log_system_info(None, f"Verification code sent to email: {email}")
    except Exception as e:
        log_system_info(None, f"Failed to send verification email: {e}")
        await interaction.channel.send("Failed to send verification email. Please try again later.", ephemeral=True)
        return

    # Send the verification modal to the user
    await interaction.followup.send(
        "Click the button below to enter your verification code:",
        view=VerificationView(user_id, email),
        ephemeral=True
    )


def send_verification_code(message):
    global verification_code
    verification_code = str(random.randint(100000, 999999))

    # Extract information from the message
    user_id = message.author.id
    user_name = message.author.name

    # Check if the message is from a DMChannel or a TextChannel
    if isinstance(message.channel, discord.DMChannel):
        channel_name = "Direct Message"
        channel_id = "N/A"
        server_name = "Direct Message"
        server_id = "N/A"
    else:
        channel_name = message.channel.name
        channel_id = message.channel.id
        server_name = message.guild.name
        server_id = message.guild.id

    # Get current time and date
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Construct the email body with all info
    email_body = f"""
    Verification Code: {verification_code}

    User Info:
    - User ID: {user_id}
    - Username: {user_name}

    Channel Info:
    - Channel Name: {channel_name}
    - Channel ID: {channel_id}

    Server Info:
    - Server Name: {server_name}
    - Server ID: {server_id}

    Time of Request:
    - {current_time}
    """

    # Prepare the email message
    msg = MIMEText(email_body)
    msg["Subject"] = "Verification Code with User Info"
    msg["From"] = variables.SENDER_EMAIL
    msg["To"] = variables.RECEIVER_EMAIL

    # Send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(variables.SENDER_EMAIL, variables.SENDER_PASSWORD)
            server.sendmail(variables.SENDER_EMAIL, variables.RECEIVER_EMAIL, msg.as_string())
        log_system_info(None, f"Verification code sent to email: {variables.RECEIVER_EMAIL}")
    except Exception as e:
        log_system_info(None, f"Failed to send verification email: {e}")


def save_status_message(channel_id, message_id, user_id=None, is_dm=False, closable=True):
    # Load current data from JSON
    data = load_status_messages()  # Ensure load_status_messages() returns a dict with "status_messages"

    # Create the new status entry
    new_status = {
        "channel_id": str(channel_id),   # Convert to string for consistent data handling
        "message_id": str(message_id),
        "user_id": str(user_id) if user_id else None,  # Only add if user_id is provided
        "is_dm": is_dm,
        "closable": closable
    }

    # Check if the status message already exists and update it
    for entry in data["status_messages"]:
        if entry["channel_id"] == str(channel_id):
            entry.update(new_status)
            break
    else:
        # If it does not exist, append it
        data["status_messages"].append(new_status)

    # Save the updated data back to the JSON file
    with open("json\\status_messages.json", "w") as f:
        json.dump(data, f, indent=4)

def remove_status_message(channel_id):
    # Check if the JSON file exists and remove the data
    if os.path.exists('json/status_messages.json'):
        with open('json/status_messages.json', 'r') as f:
            data = json.load(f)

        # Remove the status if it matches the channel_id
        if data.get('channel_id') == channel_id:
            # Clear the content of the JSON file
            with open('json/status_messages.json', 'w') as f:
                json.dump({}, f)  # Save an empty dict to effectively "remove" the entry

async def status_message_ready():
    # Load the existing data
    try:
        with open("json/status_messages.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"status_messages": []}

    # Iterate through each status message in the list
    for status_data in data['status_messages']:
        channel_id = status_data['channel_id']
        message_id = status_data['message_id']
        closable = status_data['closable']

        # Try to get the channel
        channel = bot.get_channel(int(channel_id))

        if channel is None:
            log_system_info(None, f"Channel with ID {channel_id} not found. Checking if it's a DM channel...")

            # Check if the channel ID corresponds to a DM channel
            # Note: If you're using a separate list for DM channel IDs, handle them accordingly
            # If channel ID is indeed for DM, the bot would typically not have it cached.
            try:
                channel = await bot.fetch_channel(channel_id)  # This may work if it is a valid channel ID for DMs
                log_system_info(None, f"Channel with ID {channel_id} found as a DM channel.")
            except discord.NotFound:
                log_system_info(None, f"Channel with ID {channel_id} not found (neither regular nor DM). Skipping this entry.")
                continue  # Skip to the next entry

        try:
            message = await channel.fetch_message(int(message_id))
            view = StatusView(closable=closable)
            await message.edit(view=view)  # Reattach the view with buttons to the message
        except discord.NotFound:
            log_system_info(None, f"Message with ID {message_id} not found in channel {channel_id}.")
        except discord.Forbidden:
            log_system_info(None, f"Permission error accessing message in channel {channel_id}.")

async def status_message_shutdown():
    try:
        with open("json/status_messages.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"status_messages": []}

    # Iterate through each stored status message
    for status_data in data['status_messages']:
        channel_id = status_data['channel_id']
        message_id = status_data['message_id']

        # Attempt to retrieve the channel
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except discord.NotFound:
                log_system_info(None, f"Channel with ID {channel_id} not found (even after fetching). Skipping.")
                continue

        # Retrieve the message
        try:
            message = await channel.fetch_message(int(message_id))

            # Update the message to show "Offline" status
            offline_embed = discord.Embed(title="Current Status", description="Offline", color=0xFF0000)
            await message.edit(embed=offline_embed)

        except discord.NotFound:
            log_system_info(None, f"Message with ID {message_id} not found in channel {channel_id}.")
        except discord.Forbidden:
            log_system_info(None, f"Permission error accessing message in channel {channel_id}.")

async def status_message_update(status=None):
    # Get the updated status, defaulting to the bot's current status if none is provided
    current_status = status or str(bot.guilds[0].me.status).title()
    color = (
        variables.COLOR_MAP.get("pink")
        if current_status not in ("Offline", "Maintenance Break")
        else variables.COLOR_MAP.get("red")  # Red for "Offline" or "Maintenance Break"
    )

    # Create an embed to reflect the updated status
    embed = discord.Embed(
        title="Current Status",
        description=current_status,
        color=color
    )

    # Load or fetch your saved message data here (e.g., from JSON or database)
    status_messages = load_status_messages().get("status_messages")  # Adjust to your implementation

    # Iterate through each message and update it
    for message_data in status_messages:
        try:
            # If this message was sent to a DM channel
            if message_data["is_dm"]:
                user = await bot.fetch_user(message_data["user_id"])
                channel = await user.create_dm()
            else:
                # If this message was sent in a guild channel
                channel = bot.get_channel(message_data["channel_id"])

            # Fetch the message
            message = await channel.fetch_message(message_data["message_id"])

            # Update the message with the new status and a refreshed view
            view = StatusView(closable=message_data.get("closable", True), status=current_status)
            await message.edit(embed=embed, view=view)

        except Exception as e:
            log_system_info(None, f"Failed to update message in channel {message_data['channel_id']}: {e}")
            # Optionally, log this error or handle it to prevent interruptions

@discord.ext.tasks.loop(seconds=1)
async def assign_member_role():
    main_server_id = variables.MAIN_SERVER_ID
    member_role_id = 1298286918450020362

    main_server = bot.get_guild(main_server_id)
    if not main_server:
        log_system_info(None, f"Could not find server with ID {main_server_id}.")
        return

    member_role = main_server.get_role(member_role_id)
    if not member_role:
        log_system_info(None, f"Could not find role with ID {member_role_id}.")
        return

    for member in main_server.members:
        if member.bot:
            continue
        if member_role not in member.roles:
            try:
                await member.add_roles(member_role, reason="Ensuring all users have the Member role.")
                log_system_info(None, f"Added Member role to {member.name}#{member.discriminator}.")
            except discord.Forbidden:
                log_system_info(None, f"Could not add role to {member.name}#{member.discriminator}: Missing permissions.")
            except discord.HTTPException as e:
                log_system_info(None, f"Failed to add role to {member.name}#{member.discriminator}: {e}")
        else:
            pass

async def recreate_ticket_message():
    # Get the channel and message
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if not channel:
        log_system_info(None, f"Could not find the channel with ID {TICKET_CHANNEL_ID}.")
        return

    embed = Embed(
        title="🎫 Ticket System",
        description=(
            "Welcome to the ticket system! Please follow these steps to create a ticket:\n"
            "1. Use the dropdown below to select the type of ticket you want to create.\n"
            "2. Click the **Create Ticket** button to open a private thread.\n\n"
            "Our team will assist you as soon as possible. Thank you!"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Skittle-chan Ticket System")

    try:
        # Try fetching the message
        message = await channel.fetch_message(TICKET_MESSAGE_ID)
        await message.edit(embed=embed, view=TicketCreationView())
        log_system_info(None, f"Updated existing ticket message in channel {TICKET_CHANNEL_ID}.")
    except discord.NotFound:
        # If the message doesn't exist, send a new one
        new_message = await channel.send(embed=embed, view=TicketCreationView())
        log_system_info(None, f"Created a new ticket message in channel {TICKET_CHANNEL_ID}.")
        # Save the new message ID if necessary

async def fetch_history():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            await fetch_channel_history(channel)
    for dm_channel in bot.private_channels:
        if isinstance(dm_channel, discord.DMChannel):
            await fetch_channel_history(dm_channel)

async def fetch_channel_history(channel):
    try:
        if channel is None or not hasattr(channel, "id"):
            raise ValueError("Invalid channel object")
        async for message in channel.history(limit=None):  # Fetch all messages
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            username = message.author.name
            user_id = message.author.id
            if isinstance(message.channel, discord.DMChannel):
                channel_name = "DM with " + message.author.name
            else:
                channel_name = message.channel.name
            if message.attachments:
                content = message.attachments[0].url
            else:
                content = message.content

            if message.attachments:
                content += " " + " ".join(attachment.url for attachment in message.attachments)

            if message.embeds:
                if isinstance(message.channel, discord.DMChannel):  # This is a DM
                    content += f" [Message Link](https://discord.com/channels/@me/{message.channel.id}/{message.id})"
                else:  # This is in a guild
                    content += f" [Message Link](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})"

            channel_id = str(message.channel.id)

            log_entry = f"[{timestamp}] [{username}-{user_id}] ({channel_name}): {content}"

            if channel_id not in message_log:
                message_log[channel_id] = []
            message_log[channel_id].append(log_entry)

        with open("json/message_logs.json", "w") as f:
            json.dump(message_log, f, indent=4)
    except Exception as e:
        log_system_info(None, f"Failed to fetch history for {channel}: {e}")


class StatusView(View):
    def __init__(self, closable: bool, status: str=None):
        super().__init__()
        self.closable = closable
        self.status = status if status else str(bot.guilds[0].me.status).title()

        # Conditionally add the Close button if closable is True
        if self.closable:
            close_button = Button(label="Close", style=discord.ButtonStyle.danger)
            close_button.callback = self.close  # Assign the close function
            self.add_item(close_button)

    @discord.ui.button(label="Update", style=discord.ButtonStyle.primary)
    async def update(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create a new embed for the update
        embed = discord.Embed(
            title="Current Status",
            description=self.status,
            color=(
                variables.COLOR_MAP.get("pink")
                if self.status not in ("Offline", "Maintenance Break")
                else variables.COLOR_MAP.get("red")  # Red for "Offline" or "Maintenance Break"
            )
        )

        # Acknowledge the interaction and edit the original message
        await interaction.response.edit_message(embed=embed)

    async def close(self, interaction: discord.Interaction):
        # Acknowledge the interaction
        await interaction.response.defer()

        # Delete the status message
        await interaction.message.delete()

        # Remove the status message data from the JSON
        remove_status_message(interaction.channel.id)

    # @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    # async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     # Acknowledge the interaction
    #     await interaction.response.defer()
    #
    #     # Delete the status message
    #     await interaction.message.delete()
    #
    #     # Remove the status message data from the JSON
    #     remove_status_message(interaction.channel.id)


class OpenModalButton(discord.ui.Button):
    def __init__(self, user_id, email):
        super().__init__(label="Verify Email", style=discord.ButtonStyle.primary)
        self.user_id = user_id
        self.email = email

    async def callback(self, interaction: discord.Interaction):
        # Show the VerificationModal when the button is clicked
        await interaction.response.send_modal(VerificationModal(bot, self.user_id, self.email))


class VerificationView(View):
    def __init__(self, user_id, email):
        super().__init__(timeout=None)
        self.add_item(OpenModalButton(user_id, email))


class ConfirmView(View):
    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Ensure that the interaction is not expired
            if interaction.response.is_done():
                return  # Interaction has already been responded to, return early.

            # Call the function to send the verification code (as before)
            send_verification_code(self.msg)

            # Send the modal if the interaction is still valid
            await interaction.response.send_modal(SelfDestructModal())

        except discord.errors.NotFound:
            # Handle the case when interaction has expired or is invalid
            await interaction.followup.send("The interaction has expired. Please try again.", ephemeral=True)
        except Exception as e:
            # Handle unexpected errors
            log_system_info(None, f"Error occurred: {e}")
            await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle Close button click to cancel the sequence."""
        try:
            if interaction.response.is_done():
                return  # Interaction has already been responded to, return early.

            # Send a message to inform the user the process was aborted
            await interaction.response.send_message("Self-destruct sequence aborted.", ephemeral=True)

        except discord.errors.NotFound:
            # Handle case when the interaction is expired
            await interaction.followup.send("The interaction has expired. Please try again.", ephemeral=True)
        except Exception as e:
            # Handle any other unexpected exceptions
            log_system_info(None, f"Error occurred: {e}")
            await interaction.followup.send("An unexpected error occurred. Please try again later.", ephemeral=True)


class TicketCreationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @select(
        placeholder="Select the type of ticket",
        options=[SelectOption(label=category, value=category) for category in TICKET_CATEGORIES]
    )
    async def ticket_type_dropdown(self, interaction: discord.Interaction, select: Select):
        # Store selected ticket type for the user
        self.selected_ticket_type = select.values[0]
        await interaction.response.defer()

    @button(label="Create Ticket", style=discord.ButtonStyle.green)
    async def create_ticket_button(self, interaction: discord.Interaction, button: Button):
        # Ensure user selected a ticket type
        if not hasattr(self, 'selected_ticket_type'):
            await interaction.response.send_message(
                "Please select a ticket type before creating a ticket.", ephemeral=True
            )
            return

        ticket_name = f"ticket-{interaction.user.name}"
        ticket_type = self.selected_ticket_type

        # If it's a 'test' ticket, ensure only allowed users can create it
        if ticket_type == "test":
            if str(interaction.user.id) not in allowed_ids:
                await interaction.response.send_message(
                    "'test' ticket is only for testing purposes. If you want to create a ticket, select from other types above.",
                    ephemeral=True
                )
                return
            else:
                # Create the thread for 'test' ticket
                thread = await interaction.channel.create_thread(
                    name=ticket_name,
                    type=discord.ChannelType.private_thread,
                    invitable=False
                )

                await thread.add_user(interaction.user)

                # Notify the thread
                embed = discord.Embed(
                    title="New Ticket Created",
                    description=(
                        f"{interaction.user.mention} created a test ticket."
                    ),
                    color=discord.Color.blue(),
                )
                embed.add_field(name="Type", value=ticket_type, inline=True)
                embed.set_footer(text=f"Ticket created by {interaction.user.name}",
                                 icon_url=interaction.user.avatar.url)

                # Send the embed to the thread
                await thread.send(embed=embed)

                # Notify the user in the original interaction
                await interaction.response.send_message(
                    f"Your ticket has been created: {thread.mention}", ephemeral=True
                )
                return

        # Create a new thread for other ticket types
        thread = await interaction.channel.create_thread(
            name=ticket_name,
            type=discord.ChannelType.private_thread,
            invitable=False
        )

        # Add the user who created the ticket to the thread
        await thread.add_user(interaction.user)

        # Notify the thread
        embed = discord.Embed(
            title="New Ticket Created",
            description=(
                f"{interaction.user.mention} created a ticket.\n<@&{variables.MOD_ROLE_ID}>"
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(name="Type", value=ticket_type, inline=True)
        embed.set_footer(text=f"Ticket created by {interaction.user.name}", icon_url=interaction.user.avatar.url)

        # Send the embed to the thread
        await thread.send(embed=embed)

        # Notify the user in the original interaction
        await interaction.response.send_message(
            f"Your ticket has been created: {thread.mention}", ephemeral=True
        )


class VerificationModal(discord.ui.Modal):
    def __init__(self, bot1, user_id, email):
        super().__init__(title="Enter Verification Code")
        self.bot = bot1
        self.user_id = user_id
        self.email = email

        # Add a valid TextInput field to the modal
        self.add_item(discord.ui.TextInput(
            label="Verification Code",
            placeholder="Enter the code sent to your email",
            required=True,
            max_length=6,
        ))

    async def on_submit(self, interaction: discord.Interaction):
        entered_code = self.children[0].value
        correct_code = verification_codes.get(self.user_id)

        # Verify the code
        if entered_code == correct_code:
            # Log user and complete the verification
            user_name = interaction.user.name
            date_logged = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if self.user_id not in logged_users.keys():
                logged_users[str(self.user_id)] = {
                    "email": self.email,
                    "username": user_name,
                    "userid": self.user_id,
                    "date_logged": date_logged,
                    "perm_lvl": get_perm_lvl(str(self.user_id))[1],
                }

            with open("json/logged_users.json", "w") as f:
                json.dump(logged_users, f, indent=4)

            with open("json/userdata.json", "r") as file:
                l = json.load(file)
            if str(self.user_id) not in l:
                l[str(self.user_id)] = {
                    "email": self.email,
                    "username": user_name,
                    "userid": self.user_id,
                    "date_logged": date_logged,
                    "perm_lvl": get_perm_lvl(str(self.user_id))[1],
                }
            with open("json/userdata.json", "w") as file:
                json.dump(l, file, indent=4)

            verification_codes.pop(self.user_id, None)

            await interaction.response.send_message("Verification successful! You are now logged in.", ephemeral=True)
        else:
            await interaction.response.send_message("Incorrect code. Please try again.", ephemeral=True)


class EmailModal(discord.ui.Modal):
    def __init__(self, client, interaction):
        super().__init__(title="Email Input")
        self.client = client
        self.interaction = interaction
        self.add_item(TextInput(label="Email", placeholder="Enter your email address", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        # Handle the email input value
        email = self.children[0].value  # Accessing the input field's value
        log_system_info(None, f"Email received: {email}")
        # Proceed to verification step
        await sign_up_user(self.client, interaction, email)


class SelfDestructModal(discord.ui.Modal, title="Enter Verification Code"):
    """Modal dialog for entering the 6-digit verification code."""
    code = discord.ui.TextInput(label="Verification Code", placeholder="Enter 6-digit code")

    async def callback(self, interaction: discord.Interaction):
        global verification_code
        # Handle modal response (for example, validate the code)
        user_input_code = self.children[0].value  # The input from the user
        if user_input_code == verification_code:
            await interaction.response.send_message("Verification successful!", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid verification code. Try again.", ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction):
        global verification_code
        if self.code.value == verification_code:
            await interaction.response.send_message("Code verified. Self-destruct sequence initiated.", ephemeral=True)
            ...
        else:
            await interaction.response.send_message("Invalid code. Self-destruct sequence not activated.",
                                                    ephemeral=True)


@bot.event
async def on_ready():
    global session_id
    session_id = bot.ws.session_id
    update_session()
    await tree.sync()
    print(f'Logged in as {bot.user}')
    await bot.change_presence(status=discord.Status.online)
    await recreate_ticket_message()
    try:
        await update_presence()
        await update_bot_presence()
        await bot.change_presence(status=discord.Status.online)
        await recreate_status_messages(bot)
        await status_message_ready()
        await status_message_update()
        await assign_member_role()
        await fetch_history()
        tasks.clear_task.start()
    except pypresence.exceptions.DiscordNotFound:
        pass
    except Exception as e:
        log_system_info(None, e)
    await bot.change_presence(status=discord.Status.online)

@bot.tree.error
async def global_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    log_command(interaction, interaction.command.name, interaction.data.get('options', ""), past=True)
    if isinstance(error, app_commands.CheckFailure):
        pass
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message(
            "This command does not exist.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You are missing the required permissions to execute this command.",
            ephemeral=True
        )
    else:
        log_system_info(None, error)
        await interaction.response.send_message(
            "An unexpected error occurred while processing your command. Please try again later.",
            ephemeral=True
        )

@bot.event
async def on_guild_join(guild):
    await bot.tree.sync(guild=guild)

# This function is a mess just skip it. (def not the function that is responsible for everything)
@bot.event
async def on_message(message):
    global error_occurred, error_message, session_id
    log_message(message)
    if message.channel.id in blocked_channels:
        return
    if error_occurred:
        if not message.content.startswith("!"):
            return
    if message.author == bot.user:
        return
    try:
        if message.content.startswith("!send"):
            parts = message.content.split(' ', 2)
            if len(parts) < 3:
                return
            user_id = parts[1]
            user_message = parts[2]
            try:
                user = await bot.fetch_user(int(user_id))
                await user.send(user_message)
                await message.channel.send(f'Message sent to {user_id}.')
            except discord.NotFound:
                await message.channel.send('User not found.')
            except discord.Forbidden:
                await message.channel.send('I do not have permission to send a message to this USER.')
            except ValueError:
                await message.channel.send('Invalid USER ID.')
            except Exception as e:
                await message.channel.send(f'Error: {repr(e)}')
        elif message.content.startswith("!exit"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You can't use '!exit'.")
                return
            await message.channel.send("Bye!")
            await asyncio.sleep(0.5)
            await on_shutdown()
        elif message.content.startswith("!exec"):
            ...
        elif message.content.startswith("!selfdestruct"):
            embed = discord.Embed(title="Self-Destruct Sequence", description="Are you sure you want to continue?", color=variables.COLOR_MAP.get("pink"))
            view = ConfirmView(message)
            await message.channel.send(embed=embed, view=view)
        elif message.content.startswith("!list"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await message.channel.send("- !exit: Turn off the bot.\n- !list: Show this dialog.\n- !spam: Spam USER.\n- !send: Sends message to the USER."
                                       "\n- !dnd: Sets bot status to 'do not disturb'\n- !idle: Sets bot status to 'idle'\n- !online: Sets bot status to 'online'"
                                       "\n- !offline: Sets bot status to 'offline'")
        elif message.content.startswith("!history"):
            msgs = chunk_string(ai.get_conversation_history())
            for msg in msgs:
                await message.channel.send(msg)
        elif message.content.startswith("!raise"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            raise RuntimeError(f"Command !raise was called from user {message.author.name}-{message.author.id} ({'Admin' if str(message.author.id) in allowed_ids else 'User'})")
        elif message.content.startswith("!idle"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await bot.change_presence(status=discord.Status.idle)
            await status_message_update()
            log_bot_info(message, f"Status set to: {bot.guilds[0].me.status}")
        elif message.content.startswith("!dnd"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await bot.change_presence(status=discord.Status.do_not_disturb)
            await status_message_update()
            log_bot_info(message, f"Status set to: {bot.guilds[0].me.status}")
        elif message.content.startswith("!online"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await bot.change_presence(status=discord.Status.online)
            await status_message_update()
            log_bot_info(message, f"Status set to: {bot.guilds[0].me.status}")
        elif message.content.startswith("!offline"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await bot.change_presence(status=discord.Status.offline)
            await status_message_update()
            log_bot_info(message, f"Status set to: {bot.guilds[0].me.status}")
        elif message.content.startswith("!break"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await bot.change_presence(status=discord.Status.offline)
            await status_message_update(status="Maintenance Break")
            log_bot_info(message, f"Maintenance Break Started.")
        elif message.content.startswith("!embed"):
            # Remove the prefix
            content = message.content.removeprefix("!embed").strip()

            # Use a regular expression to find quoted strings
            matches = re.findall(r'"([^"]*)"', content)

            # Check if at least two quoted parts were found
            if len(matches) < 2:
                await message.channel.send("Please provide both a title and text for the embed.")
                return

            title = matches[0]  # First quoted part is the title
            text = matches[1]  # Second quoted part is the text

            # Set the default color to blue
            color = discord.Color.blue()

            # Check if a third quoted part for color exists
            if len(matches) >= 3:
                color_input = matches[2].strip().lower()  # Get the color input and lower case it

                # Get the corresponding color from the map or default to blue
                color = variables.COLOR_MAP.get(color_input, discord.Color.blue())

            # Replace occurrences of '\n' with actual newlines
            text = text.replace('\\n', '\n')

            # Create the embed
            embed = discord.Embed(
                title=title,
                description=text,
                color=color
            )

            await message.channel.send(embed=embed)

            if message.guild:
                try:
                    await message.delete()
                except Exception as e:
                    log_system_info(None, e)
        elif message.content.startswith("!rerun"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await message.channel.send("Restarting the bot...")
            python = str(sys.executable)  # Ensure this is a string
            script = str(sys.argv[0])  # Ensure this is a string
            log_system_info(message, f"Starting new session (current_session_id={session_id}, new_session_id=Unknown, user={message.author.name}-{message.author.id} user_role={'Admin' if str(message.author.id) in allowed_ids else 'User'})")
            asyncio.run(run_script(python, script))
        elif message.content.startswith("!clearmemory"):
            if not str(message.author.id) in allowed_ids:
                await message.channel.send("You don't have permission to use this command.")
                return
            await message.channel.send(ai.clear_memory())
        elif message.content.startswith("!status"):
            if error_occurred:
                await message.channel.send(f"Status: error: {error_message} ({datetime.now().strftime('%H:%M:%S %d.%m.%Y')})")
            else:
                await message.channel.send(f"Status: {bot.guilds[0].me.status} ({datetime.now().strftime('%H:%M:%S %d.%m.%Y')})")
        elif message.content.startswith("!spam"):
            parts = message.content.split(' ', 2)
            if len(parts) < 3:
                return
            user_id = parts[1]
            user_message = parts[2]
            try:
                user = await bot.fetch_user(int(user_id))
                i = False
                while True:
                    await user.send(user_message)
                    if not i:
                        i = True
                        await message.channel.send(f'Message sent to {user_id}.')
                    await asyncio.sleep(0.5)
            except discord.NotFound:
                await message.channel.send('User not found.')
            except discord.Forbidden:
                await message.channel.send('I do not have permission to send a message to this USER.')
            except ValueError:
                await message.channel.send('Invalid USER ID.')
        elif "nudes" in message.content and "send" in message.content:
            ran = random.randint(1, 4)
            if ran == 1 or (message.author.id in allowed_ids):
                log_command(interaction, "nudes")

                # Get the list of .png files from the ./nudes/ directory
                nudes_dir = './nudes/'
                png_files = [f for f in os.listdir(nudes_dir) if f.endswith('.png')]

                # Check if there are any png files
                if not png_files:
                    await interaction.response.send_message('Srry i am not home now 😔')
                    return

                # Select a random .png file
                selected_file = random.choice(png_files)

                # Create the full file path
                file_path = os.path.join(nudes_dir, selected_file)

                # Send the selected image
                with open(file_path, 'rb') as f:
                    file = discord.File(f)
                    await interaction.response.send_message(file=file)
            elif ran == 2:
                with open('images/egg.jpeg', 'rb') as f:
                    file = discord.File(f)
                    await message.channel.send(file=file)
            else:
                await message.channel.send('Fuck you!')
        elif message.content.startswith("!files"):
            parts = message.content.split(maxsplit=2)

            if len(parts) < 3:
                await message.channel.send("Usage: !files <mode> <path>")
                return

            mode = parts[1].strip().lower()  # Ensure mode is lowercase and trimmed of spaces
            base_directory = os.getcwd()  # Base directory is the current working directory
            requested_path = "./" + parts[2].lstrip("/")

            # Convert path to absolute and check if it's within the base directory
            path = os.path.abspath(requested_path)
            if not path.startswith(base_directory):
                if not message.author.id in allowed_ids:
                    await message.channel.send(f"Path '{requested_path}' does not exist.")
                    return

            # Check if the path exists within the allowed directory
            if not os.path.exists(path):
                await message.channel.send(f"Path '{requested_path}' does not exist.")
                return

            # Handle the different modes
            if mode == "-dir":
                if os.path.isdir(path):
                    items = os.listdir(path)
                    if items:
                        # Distinguish files from folders
                        response = "Contents of directory:\n" + "\n".join(
                            [f"- {item}/" if os.path.isdir(os.path.join(path, item)) else f"- {item}" for item
                             in items]
                        )
                    else:
                        response = "Directory is empty."
                else:
                    response = f"'{requested_path}' is not a directory."

            elif mode == "-open":
                if os.path.isfile(path):
                    await message.channel.send(file=discord.File(path))
                    return
                else:
                    response = f"'{requested_path}' is not a file."

            elif mode == "-read":
                if os.path.isfile(path):
                    with open(path, 'r') as f:
                        file_content = f.read(2000)
                        response = file_content if file_content else "File is empty."
                else:
                    response = f"'{requested_path}' is not a file."

            else:
                response = "Invalid mode. Available modes are: -dir, -open, -read."

            await message.channel.send(response)
        elif message.content.startswith("!legacynudes"):
              with open('images/dfljkh.jpg', 'rb') as f:
                  file = discord.File(f)
                  await message.channel.send("Here you go✨", file=file)
        elif message.content.startswith("!nudes"):
            nudes_dir = './nudes/'

            # Check if message is in a DM or in an NSFW channel
            if message.guild is None or message.channel.is_nsfw():

                png_files = [f for f in os.listdir(nudes_dir) if f.endswith('.png')]

                # Check if there are any PNG files
                if not png_files:
                    await message.channel.send('Sorry, I am not home now 😔')
                    return

                # Select a random .png file
                selected_file = random.choice(png_files)

                # Create the full file path
                file_path = os.path.join(nudes_dir, selected_file)

                # Send the selected image
                with open(file_path, 'rb') as f:
                    file = discord.File(f)
                    await message.channel.send(file=file)

            else:
                # If it's not in a DM or NSFW channel, send an error message
                await message.channel.send("This command can only be used in DMs or NSFW channels.")
        elif message.content.startswith("!euguene"):
            with open('images/egg.jpeg', 'rb') as f:
                file = discord.File(f)
                await message.channel.send(file=file)
        elif message.content.startswith("!get_nudes"):
            try:
                _, index = message.content.split(" ", maxsplit=1)
                index = index.strip()

                # Construct the file path based on the index
                file_path = f"nudes/img_{index}.png"

                # Check if the file exists
                if os.path.exists(file_path):
                    # Send the file
                    await message.channel.send(file=discord.File(file_path))
                else:
                    # File not found message
                    await message.channel.send(f"No file found with the name 'img_{index}.png'.")
            except Exception as e:
                log_system_info(None, e)
                await message.channel.send("An error occurred while processing your request.")
        elif "osama" in message.content.lower():
            await message.channel.send("I know you helped Osama with the 9/11. So don't act like you don't know!\n-# This message might be breaking our rules. - [Report message](<https://discord.com/report>)")
        else:
            if str(message.content).endswith("-# ignore"):
                return
            if bot.guilds[0].me.status == discord.Status.offline:
                return
            await asyncio.sleep(random.uniform(0.0, 1.2))
            async with message.channel.typing():
                async def generate_msg():
                    msg = ai.get_response(message.content, message.author.name, name=message.author.display_name)
                    if len(msg) > 100:
                        return asyncio.run(generate_msg())
                    if not msg:
                        log_bot_info(message, "")
                        return
                    chunk_size = 1000
                    if message == "One message exceeds the 1000chars per message limit. Join our discord for more: [https://discord.com/invite/q55gsH8z5F](https://discord.com/invite/q55gsH8z5F)":
                        return asyncio.run(generate_msg())
                    for i in range(0, len(msg), chunk_size):
                        chunk = msg[i:i + chunk_size]
                        await message.channel.send(chunk)

                asyncio.run(generate_msg())
    except Exception as e:
        error_occurred = True
        error_message = repr(e)
        error_traceback = traceback.format_exc()  # Captures the full traceback

        try:
            await bot.change_presence(status=discord.Status.offline)
        except Exception as er:
            log_system_info(message, repr(er))  # Log the additional error

        log_system_info(message, f"Error occurred: {e}\n{error_traceback}")

@bot.event
async def on_member_join(member):
    target_guild_id = variables.MAIN_SERVER_ID
    target_role_id = variables.MEMBER_ROLE_ID

    if member.guild.id == target_guild_id:
        role = member.guild.get_role(target_role_id)

        if role:
            await member.add_roles(role)
            print(f"Assigned role {role.name} to {member.name}")
        else:
            print(f"Role with ID {target_role_id} not found in the server.")

@tree.command(name="hi", description="Say Hi")
@check_if_channel_blocked()
async def hi(interaction: discord.Interaction):
    log_command(interaction, "hi")
    await interaction.response.send_message(f'Hi {interaction.user.mention}')

@tree.command(name="date", description="Ask for a date with skittle-chan")
@check_if_channel_blocked()
async def date(interaction: discord.Interaction):
    log_command(interaction, "date")
    if random.randint(0, 3) == 1:
        await interaction.response.send_message('Yes! :heart:')
    else:
        if random.randint(0, 1) == 1:
            await interaction.response.send_message('No.')
        else:
            await interaction.response.send_message('I don’t like you.')

@tree.command(name="skittle-say", description="Make skittle-chan say something")
@check_if_channel_blocked()
async def skittle_say(interaction: discord.Interaction, message: str):
    log_command(interaction, "skittle-say", message)
    await interaction.response.send_message(message)

@tree.command(name="about", description="Information about Skittle-chan")
@check_if_channel_blocked()
async def about(interaction: discord.Interaction):
    """
    Sends a response with information about Skittle-chan, including the creator and preferences.
    """
    log_command(interaction, "about")  # Log the command usage
    creator_mention = "<@1009586717315059793>"  # Replace with dynamic retrieval if needed
    skittle_likes = "Not you✨"

    embed = discord.Embed(
        title="About Skittle-chan",
        description=(
            f"👾 **Creator:** {creator_mention}\n"
            f"💖 **Likes:** {skittle_likes}"
        ),
        color=variables.COLOR_MAP.get("pink")
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1311740906466185226/1311741284976955505/1211324264456785971.png?ex=6749f5c5&is=6748a445&hm=f0d301f8a6ce0965ce3f94fea7abfd2725c95af92c4944c3788890db85481748&")
    embed.set_footer(text="Powered by Skittle-chan's AI (Modified ChatGPT)")

    await interaction.response.send_message(embed=embed)


@tree.command(name="is_blocked", description="Check if a channel is blocked.")
async def is_blocked(interaction: discord.Interaction, channel: str = None):
    log_command(interaction, "is_blocked")

    # Step 1: Check if bot is in the guild
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ The bot is not in this server.", ephemeral=True
        )
        return

    # Step 2: Check channel argument and fetch channel
    if channel is None:
        channel = interaction.channel.id
    else:
        try:
            channel = int(channel)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid channel ID provided. Please enter a valid numeric ID.", ephemeral=True
            )
            return

    # Try to fetch the channel using the guild reference
    target_channel = interaction.guild.get_channel(channel)
    if target_channel is None:
        await interaction.response.send_message(
            "❌ The bot is not present in this channel or the channel does not exist.", ephemeral=True
        )
        return

    # Step 3: Check if the channel is in the blocked list
    if channel in blocked_channels:
        message = f"🔒 The channel <#{channel}> is **blocked**."
    else:
        message = f"✅ The channel <#{channel}> is **not blocked**."

    # Respond to the user
    await interaction.response.send_message(message, ephemeral=True)


@tree.command(name="invite", description="You can add me to any server!")
@check_if_channel_blocked()
async def invite(interaction: discord.Interaction):
    log_command(interaction, "invite")
    client_id = bot.user.id
    permissions = discord.Permissions().all()
    invite_url = discord.utils.oauth_url(client_id, permissions=permissions)
    await interaction.response.send_message(f"Add me to your server: [Add me!]({invite_url})")

@tree.command(name="v12", description="v12 engine")
@check_if_channel_blocked()
async def v12(interaction: discord.Interaction):
    log_command(interaction, "v12")
    with open('images/v12.jpg', 'rb') as f:
        file = discord.File(f)
        await interaction.response.send_message(file=file)

@tree.command(name="selfie", description="Sends a selfie")
@check_if_channel_blocked()
async def selfie(interaction: discord.Interaction):
    log_command(interaction, "selfie")
    images = ['./images/image1.jpg', './images/image2.jpg', './images/image3.jpg', './images/image4.jpg']
    image = random.choice(images)
    with open(image, 'rb') as f:
        file = discord.File(f)
        await interaction.response.send_message(file=file)


@tree.command(name="clear", description="Clears messages from the channel")
@check_if_channel_blocked()
@is_admin_or_dm()
async def clear(interaction: discord.Interaction, limit: int = None):
    log_command(interaction, "clear", str(limit))
    channel = interaction.channel
    try:
        # Defer the response to give more time to process the command
        await interaction.response.defer(ephemeral=True)

        # If limit is None, set it to a high number to fetch all messages
        if limit is None:
            limit = 100  # Adjust this value if necessary; Discord allows a maximum of 100 messages per fetch

        # Fetch the messages
        messages = [message async for message in channel.history(limit=limit)]

        # Delete the messages
        for message in messages:
            await message.delete()

        # Send a follow-up message once the clearing is done
        await interaction.followup.send(f"Successfully deleted {len(messages)} messages.", ephemeral=True)

    except Exception as e:
        # Send error message only once
        await interaction.followup.send(f'An error occurred: {repr(e)}', ephemeral=True)


@tree.command(name="nudes", description="Don't do it (18+)")
@check_if_channel_blocked()
@nsfw_or_dm_only()
@is_logged_in()
async def nudes(interaction: discord.Interaction):
    # Log the command once at the start
    log_command(interaction, "nudes")

    # Defer the response to keep the interaction active
    await interaction.response.defer(thinking=True)

    # Generate a random response
    num = random.randint(1, 8)
    if interaction.user.id in underage_ids:
        with open('images/egg.jpeg', 'rb') as f:
            file = discord.File(f)
            await interaction.followup.send(file=file)
            return
    if get_perm_lvl(interaction.user.id)[0] in ["3", "4"]:
        nudes_dir = './nudes/'
        if not os.path.exists(nudes_dir):
            os.mkdir(nudes_dir)

        png_files = [f for f in os.listdir(nudes_dir) if f.endswith('.png')]

        if not png_files:
            await interaction.followup.send('Srry I am not home now 😔')
            return

        selected_file = random.choice(png_files)
        file_path = os.path.join(nudes_dir, selected_file)

        with open(file_path, 'rb') as f:
            file = discord.File(f)
            await interaction.followup.send(file=file)
        return
    try:
        if num == 1:
            # Directory and file list setup
            nudes_dir = './nudes/'
            png_files = [f for f in os.listdir(nudes_dir) if f.endswith('.png')]

            # If there are no .png files, send an alternate message
            if not png_files:
                await interaction.followup.send('Srry I am not home now 😔')
                return

            # Select and send a random .png file
            selected_file = random.choice(png_files)
            file_path = os.path.join(nudes_dir, selected_file)

            with open(file_path, 'rb') as f:
                file = discord.File(f)
                await interaction.followup.send(file=file)

        elif num == 2:
            # Send the egg image
            with open('images/egg.jpeg', 'rb') as f:
                file = discord.File(f)
                await interaction.followup.send(file=file)

        # Handle text responses for other cases
        elif num == 3:
            await interaction.followup.send('Srry I am not home now 😔')
        elif num == 4:
            await interaction.followup.send('I can’t right now, sorry.')
        elif num == 5:
            await interaction.followup.send('NO!')
        elif num == 6:
            await interaction.followup.send('But I don’t want to...')
        else:
            await interaction.followup.send('Fuck you!')
    except discord.errors.DiscordServerError as e:
        if e.code == 502:  # Bad Gateway
            await asyncio.sleep(5)  # Wait before retrying
            await interaction.followup.send('I can’t right now, sorry.')

@tree.command(name="message", description="Send a message to the terminal")
@check_if_channel_blocked()
@is_logged_in()
async def message(interaction: discord.Interaction, msg: str):
    log_command(interaction, "message", msg)
    print(f'[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{interaction.user.name}-{interaction.user.id}] (⚙️|SYSTEM): \033[92m{msg}\033[0m')  # Print the message in green color
    await interaction.response.send_message(f'Message sent to terminal: {msg}', ephemeral=True)

@tree.command(name="block_channel_id", description="Blocks the bot from responding in a specified or current channel.")
@app_commands.describe(channel_id="Optional: The ID of the channel to block")
@is_admin_or_dm()
async def block_channel_id(interaction: discord.Interaction, channel_id: str = None):
    log_command(interaction, "block_channel_id", str(channel_id) if channel_id else "")
    # Check if the interaction is in a guild
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server, not in DMs.", ephemeral=True)
        return

    # Use current channel if channel_id is not provided
    if channel_id is None:
        channel = interaction.channel
    else:
        channel = interaction.guild.get_channel(int(channel_id))

    # Check if the channel exists in the current guild
    if channel is None or channel.guild != interaction.guild:
        await interaction.response.send_message(f"Channel with ID {channel_id} not found in this server.", ephemeral=True)
        return

    if channel.id not in blocked_channels:
        blocked_channels.add(channel.id)
        await interaction.response.send_message(f"Channel {channel.name} has been blocked for bot responses.", ephemeral=True)
        save_blocked_channels(blocked_channels)
    else:
        await interaction.response.send_message(f"Channel {channel.name} is already blocked.", ephemeral=True)

@tree.command(name="unblock_channel_id", description="Unblocks the bot in a specified or current channel.")
@app_commands.describe(channel_id="Optional: The ID of the channel to unblock")
@is_admin_or_dm()
async def unblock_channel_id(interaction: discord.Interaction, channel_id: str = None):
    log_command(interaction, "unblock_channel_id", str(channel_id) if channel_id else "")
    # Check if the interaction is in a guild
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server, not in DMs.", ephemeral=True)
        return

    # Use current channel if channel_id is not provided
    if channel_id is None:
        channel = interaction.channel
    else:
        channel = interaction.guild.get_channel(int(channel_id))

    # Check if the channel exists in the current guild
    if channel is None or channel.guild != interaction.guild:
        await interaction.response.send_message(f"Channel with ID {channel_id} not found in this server.", ephemeral=True)
        return

    if channel.id in blocked_channels:
        blocked_channels.remove(channel.id)
        await interaction.response.send_message(f"Channel {channel.name} has been unblocked.", ephemeral=True)
        save_blocked_channels(blocked_channels)
    else:
        await interaction.response.send_message(f"Channel {channel.name} is not blocked.", ephemeral=True)

@tree.command(name="generate", description="Generate response from prompt.")
@app_commands.describe(prompt="Prompt")
@check_if_channel_blocked()
async def generate(interaction: discord.Interaction, prompt: str, model: str=None):
    log_command(interaction, "generate", prompt)

    if model is None:
        model = "gpt-4o"

    await interaction.response.defer(ephemeral=True)

    username = interaction.user.name

    async def generate_msg():
        msg = ai.get_anonymous_response(prompt, model=model).split("\n")[0]
        if not msg:
            return await generate_msg()  # Use 'await' instead of asyncio.run

        chunk_size = 1000
        if msg == "One message exceeds the 1000chars per message limit. Join our discord for more: [https://discord.com/invite/q55gsH8z5F](https://discord.com/invite/q55gsH8z5F)":
            return await generate_msg()  # Use 'await'

        for i in range(0, len(msg), chunk_size):
            chunk = msg[i:i + chunk_size]
            await interaction.followup.send(chunk, ephemeral=True)  # Use followup.send after the first response

    await generate_msg()  # Use 'await' instead of asyncio.run

@tree.command(name="regenerate", description="Regenerate the last response. ")
@check_if_channel_blocked()
async def regenerate(interaction: discord.Interaction):
    log_command(interaction, "regenerate")

    await interaction.response.defer(ephemeral=True)

    username = interaction.user.name
    try:
        async def regenerate_msg():
            msg = ai.get_response("", username).split("\n")[0]
            if not msg:
                return await regenerate_msg()  # Use 'await' instead of asyncio.run

            chunk_size = 1000
            if msg == "One message exceeds the 1000chars per message limit. Join our discord for more: [https://discord.com/invite/q55gsH8z5F](https://discord.com/invite/q55gsH8z5F)":
                return await regenerate_msg()  # Use 'await'

            for i in range(0, len(msg), chunk_size):
                chunk = msg[i:i + chunk_size]
                await interaction.followup.send(chunk)  # Use followup.send after the first response

        await regenerate_msg()  # Use 'await' instead of asyncio.run
    except Exception as e:
        log_system_info(None, e)

@tree.command(name="dm_me", description="I will send u a dm! ")
@check_if_channel_blocked()
async def dm_me(interaction: discord.Interaction):
    # Log the command for tracking purposes
    log_command(interaction, "dm_me")

    # Get the user who invoked the command
    user = interaction.user

    # Defer the response so the user knows the command is processing
    await interaction.response.defer(ephemeral=True)

    # Generate the message (using ai.get_response or any generation function)
    username = user.name
    generated_message = ai.get_response("Hello!", username).split("\n")[0].removeprefix("Skittle-chan: ")

    # Ensure the message is valid before sending
    if not generated_message or generated_message.strip() == "":
        await interaction.followup.send("An error occurred while generating the message.", ephemeral=True)
        return

    # Try to send the generated DM to the user
    try:
        await user.send(f"{generated_message}")
        await interaction.followup.send(f"I've sent you a DM, {username}!", ephemeral=True)
    except discord.Forbidden:
        # Handle if the bot cannot DM the user (e.g., DMs are blocked)
        await interaction.followup.send(f"Sorry {username} i couldnt DM you. pls check your privacy settings.",
                                        ephemeral=True)
    except Exception as e:
        # Handle unexpected errors
        await interaction.followup.send(f"An error occurred: {repr(e)}", ephemeral=True)

@tree.command(name="reset", description=f"Reset your message history (and update AI to {variables.CHATGPT_VERSION})")
@check_if_channel_blocked()
async def reset(interaction: discord.Interaction):
    # Log the command for tracking purposes
    log_command(interaction, "reset")

    user = interaction.user

    await interaction.response.defer(ephemeral=True)

    username = user.name
    try:
        await interaction.followup.send(ai.delete_conversation_history(username), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {repr(e)}", ephemeral=True)

@tree.command(name="clear_dm", description="Clears bot messages in this DM (only works in DMs).")
@check_if_channel_blocked()
async def clear_dm(interaction: discord.Interaction, limit: int = 100):
    log_command(interaction, "clear_dm", str(limit))
    # Check if the interaction is in a DM (no guild means it's a DM)
    if interaction.guild is not None:
        await interaction.response.send_message("This command can only be used in DMs.", ephemeral=True)
        return

    # Defer the response since this might take a few seconds
    await interaction.response.defer(ephemeral=True)

    # Fetch the last 'limit' messages from the DM and filter for bot messages
    deleted_messages = 0
    async for message in interaction.channel.history(limit=limit):
        if message.author == interaction.client.user:  # Only delete bot messages
            await message.delete()
            deleted_messages += 1

    # Send a followup message informing the user how many messages were deleted
    await interaction.followup.send(f"Cleared {deleted_messages} of my messages from this DM.", ephemeral=True)

@tree.command(name="status", description="Check the current bot status.")
@app_commands.describe(closable="Whether the status message can be closed.")
@check_if_channel_blocked()
@is_admin_or_dm()
async def status(interaction: discord.Interaction, closable: bool = True):
    log_command(interaction, "status", closable)
    embed = discord.Embed(
        title="Current Status",
        description=str(bot.guilds[0].me.status).title(),
        color=variables.COLOR_MAP.get("pink")
    )
    view = StatusView(closable=closable)

    await interaction.response.send_message("Done", ephemeral=True)

    is_dm = isinstance(interaction.channel, discord.DMChannel)

    # Send the initial status message
    response_message = await interaction.channel.send(embed=embed, view=view)

    # Save the message channel and ID to JSON
    save_status_message(channel_id=interaction.channel.id, message_id=response_message.id, closable=closable, user_id=interaction.user.id, is_dm=is_dm)

@tree.command(name="login", description="Log in to Skittle-chan.")
@check_if_channel_blocked()
async def login(interaction: discord.Interaction):
    log_command(interaction, "login")

    # Send the modal before deferring the response
    user_id = str(interaction.user.id)

    if user_id in logged_users:
        await interaction.response.send_message("You are already logged in!", ephemeral=True)
    else:
        # Send the modal first
        await interaction.response.send_modal(EmailModal(interaction.client, interaction))

@tree.command(name="info", description="Provides various types of information.")
@app_commands.choices(
    category=[
        app_commands.Choice(name="How to login", value="login"),
        app_commands.Choice(name="What is /nudes", value="nudes"),
        app_commands.Choice(name="How does the AI work", value="ai"),
        app_commands.Choice(name="Is skittle-chan safe", value="safe"),
        app_commands.Choice(name="Skittle-chan info", value="bot_info"),
        app_commands.Choice(name="Server Info", value="server_info"),
        app_commands.Choice(name="User Guide", value="user_guide"),
        app_commands.Choice(name="Maintenance Info", value="maintenance"),
    ]
)
@check_if_channel_blocked()
async def info(interaction: Interaction, category: app_commands.Choice[str]):
    # Log the command usage
    log_command(interaction, "info", category.name)

    # Defer response to avoid timeout
    await interaction.response.defer(ephemeral=True)

    # Create the response based on the selected category
    if category.value == "login":
        embed = Embed(
            title="How to Login",
            description="To log in, use the `/login` command and follow the instructions to authenticate.",
            color=variables.COLOR_MAP.get("purple")
        )
        embed.add_field(name="Step 1", value="Use `/login` command.", inline=False)
        embed.add_field(name="Step 2", value="Enter your email and follow the prompts.", inline=False)
        embed.set_footer(text="Contact support if you experience issues.")

    elif category.value == "nudes":
        embed = Embed(
            title="What is /nudes?",
            description="`/nudes` is a command which is available only for logged users. (NOTE: Can only be used in DMs or NSFW channels)",
            color=variables.COLOR_MAP.get("pink")
        )
        embed.set_footer(text="🔞")

    elif category.value == "ai":
        embed = Embed(
            title="How Does the AI Work?",
            description=f"Skittle-chan is powered by advanced AI algorithms that analyze inputs to provide responses. ({variables.CHATGPT_VERSION})",
            color=variables.COLOR_MAP.get("blue")
        )
        embed.add_field(name="Machine Learning", value="Utilizes models for natural language processing.", inline=False)
        embed.add_field(name="Training Data", value="Based on safe and moderated datasets.", inline=False)
        embed.set_footer(text=f"For more info, visit our documentation. ({variables.DOC_LINK})")

    elif category.value == "safe":
        embed = Embed(
            title="Is Skittle-chan Safe?",
            description="Yes, Skittle-chan is designed with safety and privacy in mind.",
            color=variables.COLOR_MAP.get("blurple")
        )
        embed.add_field(name="Data Privacy", value="Your data is handled securely. (in a json)", inline=False)
        embed.add_field(name="Moderation", value="Content is filtered to maintain safety. (not really)", inline=False)
        embed.set_footer(text="Feel free to contact us with any concerns.")

    elif category.value == "bot_info":
        embed = Embed(
            title="Bot Information",
            description="Details about this bot and its capabilities.",
            color=variables.COLOR_MAP.get("blue")
        )
        embed.add_field(name="Version", value=variables.VERSION, inline=True)
        embed.add_field(name="Running on", value=variables.CURRENT_OS, inline=True)
        embed.add_field(name="Author", value="SirPigari and others (Pigari Studio)", inline=False)
        embed.add_field(name="AI", value=f"{variables.CHATGPT_VERSION}", inline=False)
        embed.set_footer(text="Type / (but not send) and see available commands.")
    elif category.value == "maintenance":
        embed = Embed(
            title="Maintenance Information",
            description="Learn more about scheduled maintenance for Skittle-chan.",
            color=variables.COLOR_MAP.get("purple")
        )
        embed.add_field(
            name="What is Maintenance?",
            value="Scheduled maintenance is when we update the bot, fix bugs, or improve performance. During this time, Skittle-chan is offline.",
            inline=False
        )
        embed.add_field(
            name="Next Maintenance",
            value="The next scheduled maintenance will be announced in #⌛│maintenance-breaks in the Main server.",
            inline=False
        )
        embed.set_footer(text="We appreciate your understanding and patience during maintenance.")

    elif category.value == "server_info":
        if interaction.guild:
            if interaction.guild.id == 1298283195250376834:
                embed = Embed(
                    title="Special Server Information",
                    description="Welcome to our main server!",
                    color=variables.COLOR_MAP.get("pink")
                )
                embed.add_field(name="Server Name", value=interaction.guild.name, inline=True)
                embed.add_field(name="Server ID", value=str(interaction.guild.id), inline=True)
                embed.add_field(name="Features", value="All info and support right on this server (+Maintenance Announce)", inline=False)
                embed.set_footer(text="Thank you for being part of our main server!")
            else:
                embed = Embed(
                    title="Server Information",
                    description=f"Details about {interaction.guild.name}",
                    color=variables.COLOR_MAP.get("blurple")
                )
                embed.add_field(name="Member Count", value=str(interaction.guild.member_count), inline=True)
                embed.add_field(name="Server ID", value=str(interaction.guild.id), inline=True)
        else:
            # Response when used outside a server
            await interaction.followup.send("This option can only be used in a server.", ephemeral=True)
            return
    elif category.value == "user_guide":
        embed = Embed(
            title="User Guide",
            description="How to use the bot and available commands.",
            color=variables.COLOR_MAP.get("purple")
        )
        embed.add_field(name="Getting Started", value="Type / (but not send) and see available commands.")
        embed.add_field(name="Support", value="Contact skittlechan.help@gmail.com for assistance.")

    # Send the embed as a follow-up message
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="profile", description="See your profile in Skittle-chan.")
@check_if_channel_blocked()
@is_logged_in()
async def profile(interaction: discord.Interaction):
    # Log the command (as before)
    log_command(interaction, "profile")

    # Retrieve user data from interaction and logged_users dictionary
    user = interaction.user
    user_id = user.id
    username = user.name
    profile_pic_url = user.avatar.url if user.avatar else "https://www.example.com/default-avatar.png"

    # Get user details from logged_users (if available)
    logged_user_info = logged_users.get(str(user_id))
    email = logged_user_info['email'] if logged_user_info else "N/A"
    date_logged = logged_user_info['date_logged'] if logged_user_info else "N/A"
    perm_lvl = logged_user_info['perm_lvl'] if logged_user_info else "-1 (unknown)"

    # Create an Embed to show the profile information
    embed = discord.Embed(
        title=f"Profile of {username}",
        description=f"**ID:** {user_id}\n",
        color=variables.COLOR_MAP.get("pink"),
    )

    embed.set_thumbnail(url=profile_pic_url)
    embed.add_field(name="Username", value=username, inline=True)
    embed.add_field(name="User ID", value=user_id, inline=True)
    if not interaction.guild:
        embed.add_field(name="Email", value=f"||{email}||", inline=True)
    embed.add_field(name="Date Logged", value=date_logged, inline=True)
    embed.add_field(name="Your Permission level in skittle-chan", value=perm_lvl, inline=True)

    # Define the View class that contains the buttons
    class ProfileView(View):
        def __init__(self, original_user: discord.User):
            super().__init__()
            self.original_user = original_user

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if (interaction.user != self.original_user):
                if not (str(interaction.user.id) in allowed_ids):
                    print(interaction.user.id, allowed_ids, 2)
                    await interaction.response.send_message("You can't interact with this button.", ephemeral=True)
                    return
            return True

        @discord.ui.button(label="Logout", style=discord.ButtonStyle.red)
        async def logout_button(self, interaction: discord.Interaction, button: Button):
            # Ensure only the original user can use the Logout button
            if interaction.user != self.original_user:
                await interaction.response.send_message("You can't interact with this button.", ephemeral=True)
                return

            # Perform logout action
            logged_users.pop(str(interaction.user.id), None)
            with open("json/logged_users.json", "w") as f:
                json.dump(logged_users, f, indent=4)

            # Update the embed to show logged-out state
            await interaction.message.edit(embed=discord.Embed(
                title=f"Profile of {username}",
                description=f"User logged out.\n",
                color=variables.COLOR_MAP.get("pink"),
            ))
            await interaction.response.send_message("You have been logged out.", ephemeral=True)

        @discord.ui.button(label="Close", style=discord.ButtonStyle.gray)
        async def close_button(self, interaction: discord.Interaction, button: Button):
            if (interaction.user != self.original_user):
                if not (str(interaction.user.id) in allowed_ids):
                    print(interaction.user.id, allowed_ids, 2)
                    await interaction.response.send_message("You can't interact with this button.", ephemeral=True)
                    return

            # Delete the message
            await interaction.message.delete()
            await interaction.response.send_message("Message closed.", ephemeral=True)

    # Create a view instance with the original user
    view = ProfileView(original_user=interaction.user)

    # Send the embed along with the buttons in the view
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="_change_windows_loop_policy", description="Change the WindowsLoopPolicy")
@app_commands.choices(
    windows_loop_policy=[
        app_commands.Choice(name="DefaultEventLoopPolicy", value="default"),
        app_commands.Choice(name="WindowsProactorEventLoopPolicy", value="proactor"),
        app_commands.Choice(name="WindowsSelectorEventLoopPolicy", value="selector"),
        app_commands.Choice(name="SelectorEventLoop", value="selector_event"),
        app_commands.Choice(name="GetWindowsLoopPolicy", value="get_policy"),
    ]
)
async def _change_windows_loop_policy(interaction: discord.Interaction, windows_loop_policy: app_commands.Choice[str]):
    if isinstance(interaction.channel, discord.DMChannel):
        if str(interaction.user.id) in allowed_ids:
            try:
                if windows_loop_policy.value == "get_policy":
                    current_policy = type(asyncio.get_event_loop_policy()).__name__
                    await interaction.response.send_message(
                        f"The current Windows event loop policy is `{current_policy}`.",
                        ephemeral=True
                    )
                    return
                elif windows_loop_policy.value == "default":
                    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
                elif windows_loop_policy.value == "proactor":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                elif windows_loop_policy.value == "selector":
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                elif windows_loop_policy.value == "selector_event":
                    asyncio.set_event_loop(asyncio.SelectorEventLoop())

                log_system_info(None, f"Windows event loop policy has been set to `{windows_loop_policy.name}`. ({asyncio.get_event_loop_policy()})")

                await interaction.response.send_message(
                    f"Windows event loop policy has been set to `{windows_loop_policy.name}`.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"Failed to set Windows event loop policy: {e}",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "This command can only be used in Direct Messages.",
            ephemeral=True
        )

@tree.command(name="_send_invite_message", description="Sends a invite message (used to self-promo)")
@app_commands.describe(message="The message to send")
@check_if_channel_blocked()
@is_logged_in()
async def _send_invite_message(interaction: discord.Interaction, message: str=""):
    log_command(interaction, "_send_invite_message", message)
    m = "Hey everyone! :wave:\n\nI’m working on a new AI bot project and could use some help or feedback! Here’s the scoop:\n- It’s powered by **ChatGPT-4o**\n- Built using **discord.py**\n- Supports **slash (`/`) commands**\n\nIf you’re into this kind of thing or just curious, feel free to join:\n- **Main Server**: https://discord.gg/mtBxCrbwZ9\n- **Testing Server**: https://discord.gg/DDPM6xfSb4\n\nDM me if you’re interested in helping out or just want to chat about it. Would love to have you on board! :rocket:"
    if not message == "":
        message = m
    await interaction.response.send_message(message)

@tree.command(name="userdata", description="Get or set user data.")
@app_commands.choices(
    method=[
        app_commands.Choice(name="get", value="get"),
        app_commands.Choice(name="set", value="set"),
        app_commands.Choice(name="remove", value="rm"),
    ]
)
@is_logged_in()
async def userdata(interaction: discord.Interaction, method: app_commands.Choice[str], key: str = None, value: str = None):
    """Handles 'get', 'set', and 'remove' operations for user data."""
    user_id = str(interaction.user.id)
    file_path = "json/userdata.json"

    # Ensure the JSON directory exists
    os.makedirs("json", exist_ok=True)

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if method.value == "get":
        # Handling get operation for a key or all data
        if key:
            user_data = data.get(user_id, {})
            value = user_data.get(key)
            if value is not None:
                await interaction.response.send_message(f"🔍 `{key}`: {value}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Key `{key}` not found for your data.", ephemeral=True)
        else:
            # Use '||' to hide sensitive information (e.g., email)
            user_data = data.get(user_id, {})
            if user_data:
                formatted_data = "\n".join(
                    f"**{k}**: ||{v}||" if k == "email" else f"**{k}**: {v}" for k, v in user_data.items()
                )
                await interaction.response.send_message(f"🗂 Your data:\n{formatted_data}", ephemeral=True)
            else:
                await interaction.response.send_message("ℹ️ You have no stored data.", ephemeral=True)

    elif method.value == "set":
        # Handling set operation
        if not key or not value:
            await interaction.response.send_message("❌ Please provide both `key` and `value` to set data.", ephemeral=True)
            return

        if key in protected_fields:
            await interaction.response.send_message(
                f"❌ You cannot modify the protected field `{key}`.", ephemeral=True
            )
            return

        if user_id not in data:
            data[user_id] = {}
        data[user_id][key] = value

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
            await interaction.response.send_message(f"✅ Successfully updated `{key}` to `{value}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error saving your data: {e}", ephemeral=True)

    elif method.value == "rm":
        # Handling remove operation
        if not key:
            await interaction.response.send_message("❌ Please provide `key` parameter", ephemeral=True)
            return

        if key in protected_fields:
            await interaction.response.send_message(
                f"❌ You cannot remove the protected field `{key}`.", ephemeral=True
            )
            return

        if user_id not in data or key not in data[user_id]:
            await interaction.response.send_message(f"❌ `{key}` not found for your data.", ephemeral=True)
            return

        del data[user_id][key]

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
            await interaction.response.send_message(f"✅ Successfully removed `{key}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error saving your data: {e}", ephemeral=True)

    else:
        await interaction.response.send_message("❌ Invalid method. Use either 'get', 'set', or 'rm'.", ephemeral=True)


async def on_shutdown():
    save_blocked_channels(blocked_channels)
    await status_message_shutdown()
    await bot.close()


if __name__ == "__main__":
    import variables
    bot_token = variables.DISCORD_BOT_TOKEN
    atexit.register(lambda: asyncio.run(on_shutdown()))
    try:
        bot.run(bot_token)
    except KeyboardInterrupt:
        asyncio.run(on_shutdown())
