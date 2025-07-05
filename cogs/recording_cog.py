import discord
from discord.ext import commands
import json
from core.session_manager import RecordingSessionManager

class RecordingCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.session_manager = RecordingSessionManager(bot, bot.transcription_queue)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        try:
            with open(f"config_{member.guild.id}.json", "r") as f:
                config = json.load(f)
            target_category_id = config.get("target_category_id")
        except Exception:
            return

        # join
        if before.channel is None and after.channel is not None:
            if after.channel.category_id == target_category_id:
                await self.session_manager.start_recording(member, after.channel)
        # leave
        elif before.channel is not None and after.channel is None:
            await self.session_manager.stop_recording(member)
