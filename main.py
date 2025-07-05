import os
import asyncio
import discord
from dotenv import load_dotenv
import aiodiskqueue

from core.transcription_worker import transcription_worker
load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user}としてログインしました。")


async def setup_bot():
    queue_path = os.path.join(".", "data", "queue")
    os.makedirs(queue_path, exist_ok=True)
    queue = await aiodiskqueue.Queue.create(queue_path)
    bot.transcription_queue = queue

    from cogs import setup_cog, recording_cog
    bot.add_cog(setup_cog.SetupCog(bot))
    bot.add_cog(recording_cog.RecordingCog(bot))

    bot.loop.create_task(transcription_worker(bot))

if __name__ == "__main__":
    asyncio.run(setup_bot())
    bot.run(os.getenv("DISCORD_TOKEN"))
