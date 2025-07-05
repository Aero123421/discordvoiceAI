const { Client, GatewayIntentBits } = require('discord.js');
const { joinVoiceChannel, EndBehaviorType } = require('@discordjs/voice');
const prism = require('prism-media');
const fs = require('fs');
const { spawn } = require('child_process');
const path = require('path');
require('dotenv').config();

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates],
});

const sessions = new Map();

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
  ff.on('exit', () => {
    const py = spawn('python3', [path.join(__dirname, 'transcribe.py'), wavPath]);
    let output = '';
    py.stdout.on('data', (data) => {
      output += data.toString();
    });
    py.stderr.on('data', (data) => {
      console.error(`Python error: ${data}`);
    });
    py.on('close', () => {
      const channel = member.guild.systemChannel;
      if (channel) {
        channel.send(`${member} の文字起こし結果:\n${output.trim() || '取得できませんでした'}`);
      }
      fs.unlink(pcmPath, () => {});
      fs.unlink(wavPath, () => {});
    });
  });
}

client.login(process.env.DISCORD_TOKEN);

