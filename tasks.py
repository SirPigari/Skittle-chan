import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta

@tasks.loop(hours=24)
async def clear_task():
    now = datetime.utcnow()
    # Check if the current time is midnight (00:00)
    if now.hour == 0 and now.minute == 0:
        # Specify the channel ID where you want to clear messages
        channel_id = 1298283256516706365  # Replace with your channel ID
        channel = bot.get_channel(channel_id)

        if channel:
            try:
                # Clear messages from the channel
                messages = [message async for message in channel.history(limit=100)]  # Adjust the limit if needed
                for message in messages:
                    await message.delete()
                print(f"Successfully deleted {len(messages)} messages in channel {channel.name}.")
            except Exception as e:
                print(f'An error occurred while clearing messages: {repr(e)}')


@clear_task.before_loop
async def before_clear_task():
    # Wait until midnight to start the task
    now = datetime.utcnow()
    target_time = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    await discord.utils.sleep_until(target_time)