import os
import json
import time
import discord
from discord.ext import tasks

from .gemini_processor import GeminiProcessor


class RecordingSession:
    def __init__(
        self,
        member: discord.Member,
        voice_client: discord.VoiceClient,
        manager,
    ):
        self.member = member
        self.vc = voice_client
        self.manager = manager
        self.transcript_segments: list[str] = []
        self.chunk_task = self.create_task()

    def create_task(self):
        @tasks.loop(minutes=5.0)
        async def chunker():
            if self.vc.recording:
                self.vc.stop_recording()

        @chunker.before_loop
        async def before_chunker():
            self.vc.start_recording(
                discord.sinks.WaveSink(),
                self.manager.once_done_callback,
                self.member,
            )
        return chunker

    def start(self):
        self.chunk_task.start()

    def stop(self):
        self.chunk_task.cancel()
        if self.vc.recording:
            self.vc.stop_recording()


class RecordingSessionManager:
    def __init__(self, bot: discord.Bot, queue):
        self.bot = bot
        self.gemini = GeminiProcessor()
        self.active_sessions: dict[int, RecordingSession] = {}
        self.queue = queue

    async def start_recording(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
    ):
        if member.id in self.active_sessions:
            return
        vc = await channel.connect()
        session = RecordingSession(member, vc, self)
        self.active_sessions[member.id] = session
        session.start()

    async def stop_recording(self, member: discord.Member):
        session = self.active_sessions.pop(member.id, None)
        if session:
            session.stop()
            if session.vc.is_connected():
                await session.vc.disconnect()
            final_text = "".join(session.transcript_segments)
            result = await self.gemini.process_transcript(final_text)
            content = result.get("full_transcript", final_text)
            channel_id = self.get_output_channel(member.guild)
            if channel_id:
                channel = member.guild.get_channel(channel_id)
                if channel:
                    await channel.send(content)

    def get_session(self, user_id: int):
        return self.active_sessions.get(user_id)

    def get_output_channel(self, guild: discord.Guild):
        try:
            with open(f"config_{guild.id}.json", "r") as f:
                data = json.load(f)
            return data.get("output_channel_id")
        except Exception:
            return None

    async def once_done_callback(
        self,
        sink: discord.sinks.WaveSink,
        member: discord.Member,
        *args,
    ):
        user_audio = sink.audio_data.get(member.id)
        if not user_audio:
            return
        os.makedirs("data/recordings", exist_ok=True)
        file_path = f"data/recordings/{member.id}_{int(time.time())}.wav"
        with open(file_path, "wb") as f:
            f.write(user_audio.file.getbuffer())
        await self.queue.put((member.id, file_path))
        session = self.get_session(member.id)
        if session and session.vc.is_connected():
            session.vc.start_recording(
                discord.sinks.WaveSink(),
                self.once_done_callback,
                member,
            )
