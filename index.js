const { Client, GatewayIntentBits } = require('discord.js');
const { joinVoiceChannel, EndBehaviorType } = require('@discordjs/voice');
const prism = require('prism-media');
const fs = require('fs');
const { spawn } = require('child_process');
const { OpenAI } = require('openai');
const path = require('path');
require('dotenv').config();

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates],
});

const sessions = new Map();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

client.once('ready', () => {
  console.log(`${client.user.tag} としてログインしました。`);
});

client.on('voiceStateUpdate', async (oldState, newState) => {
  const member = newState.member || oldState.member;
  if (!member || member.user.bot) return;

  if (!oldState.channel && newState.channel) {
    const connection = joinVoiceChannel({
      channelId: newState.channel.id,
      guildId: newState.channel.guild.id,
      adapterCreator: newState.channel.guild.voiceAdapterCreator,
      selfDeaf: false,
    });

    const receiver = connection.receiver;
    const userId = member.id;
    const pcm = fs.createWriteStream(
      path.join(__dirname, 'data', 'recordings', `${userId}_${Date.now()}.pcm`)
    );
    sessions.set(userId, { connection, pcmPath: pcm.path });

    receiver.speaking.on('start', (uid) => {
      if (uid !== userId) return;
      const opusStream = receiver.subscribe(uid, { end: { behavior: EndBehaviorType.Manual } });
      const decoder = new prism.opus.Decoder({ rate: 48000, channels: 2, frameSize: 960 });
      opusStream.pipe(decoder).pipe(pcm);
    });
  }

  if (oldState.channel && !newState.channel) {
    const session = sessions.get(member.id);
    if (session) {
      session.connection.destroy();
      sessions.delete(member.id);
      session.pcmPath && session.pcmPath.endsWith('.pcm') && transcribe(session.pcmPath, member);
    }
  }
});

function transcribe(pcmPath, member) {
  const wavPath = pcmPath.replace(/\.pcm$/, '.wav');
  const ff = spawn('ffmpeg', [
    '-y',
    '-f',
    's16le',
    '-ar',
    '48k',
    '-ac',
    '2',
    '-i',
    pcmPath,
    wavPath,
  ]);
  ff.on('exit', async () => {
    try {
      const response = await openai.audio.transcriptions.create({
        file: fs.createReadStream(wavPath),
        model: 'whisper-1',
      });
      const channel = member.guild.systemChannel;
      if (channel) {
        channel.send(`${member} の文字起こし結果:\n${response.text || '取得できませんでした'}`);
      }
    } catch (err) {
      console.error('Transcription error:', err);
    } finally {
      fs.unlink(pcmPath, () => {});
      fs.unlink(wavPath, () => {});
    }
  });
}

client.login(process.env.DISCORD_TOKEN);

