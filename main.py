import os
import asyncio
import discord
from dotenv import load_dotenv
import aiodiskqueue

from core.transcription_worker import transcription_worker


def ensure_directories() -> None:
    for path in (os.path.join("data", "queue"), os.path.join("data", "recordings")):
        os.makedirs(path, exist_ok=True)


def ensure_env() -> None:
    if os.path.exists(".env"):
        load_dotenv()
        return

    if not os.path.exists(".env.example"):
        with open(".env.example", "w") as f:
            f.write(
                "DISCORD_TOKEN=\"YOUR_DISCORD_BOT_TOKEN\"\n"
                "GEMINI_API_KEY=\"YOUR_GEMINI_API_KEY\"\n"
                "TRANSCRIPTION_MODEL=\"small\"\n"
                "GEMINI_MODEL=\"gemini-2.5-flash\"\n"
            )
    print(".env が見つかりませんでした。 .env.example を生成しました。必要事項を記入し .env を作成してください。")


ensure_directories()
ensure_env()

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
