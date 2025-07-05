import os
import asyncio
from faster_whisper import WhisperModel

async def transcription_worker(bot):
    model_size = os.getenv("TRANSCRIPTION_MODEL", "small")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    print(f"Faster-Whisperモデル({model_size})をロードしました。")
    loop = asyncio.get_running_loop()
    while True:
        user_id, audio_path = await bot.transcription_queue.get()
        segments, _ = await loop.run_in_executor(None, lambda: model.transcribe(audio_path))
        text = "".join(seg.text for seg in segments)
        session = bot.get_cog("RecordingCog").session_manager.get_session(user_id)
        if session:
            session.transcript_segments.append(text)
        bot.transcription_queue.task_done()
