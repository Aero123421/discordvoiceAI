import os
import asyncio
import discord
from dotenv import load_dotenv
import aiodiskqueue

from core.session_manager import RecordingSessionManager
from core.transcription_worker import transcription_worker
from cogs import setup_cog, recording_cog


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
                "TEST_GUILD_ID=\"YOUR_TEST_GUILD_ID\"\n"
            )
    print(".env が見つかりませんでした。 .env.example を生成しました。必要事項を記入し .env を作成してください。")


ensure_directories()
ensure_env()

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True


class MyBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transcription_queue = None
        self.session_manager = None

    async def setup_hook(self):
        os.makedirs(os.path.join("data", "queue"), exist_ok=True)
        os.makedirs(os.path.join("data", "recordings"), exist_ok=True)

        queue_path = os.path.join(".", "data", "queue")
        self.transcription_queue = await aiodiskqueue.Queue.create(queue_path)
        self.session_manager = RecordingSessionManager(
            self, self.transcription_queue
        )

        self.add_cog(setup_cog.SetupCog(self))
        self.add_cog(recording_cog.RecordingCog(self))

        self.loop.create_task(transcription_worker(self))
        print("セットアップが完了し、文字起こしワーカーが起動しました。")


test_guild = os.getenv("TEST_GUILD_ID")
test_guilds = [int(test_guild)] if test_guild else None
bot = MyBot(intents=intents, test_guilds=test_guilds)


@bot.event
async def on_ready():
    print(f"{bot.user}としてログインしました。")
    try:
        await bot.sync_commands()
        print("スラッシュコマンドを同期しました。")
    except Exception as e:
        print(f"コマンド同期中にエラーが発生しました: {e}")


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not token or not gemini_key:
        print("エラー: .envファイルにDISCORD_TOKENとGEMINI_API_KEYを設定してください。")
    else:
        bot.run(token)
