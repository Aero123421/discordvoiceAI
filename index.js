const { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder } = require('discord.js');
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

// Define a simple ping command
const commands = [
  new SlashCommandBuilder().setName('ping').setDescription('Replies with Pong!'),
].map(command => command.toJSON());

// Register slash commands
client.once('ready', async () => {
  console.log(`${client.user.tag} としてログインしました。`);
  try {
    console.log('Started refreshing application (/) commands.');
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    // For guild-specific commands (faster updates for testing)
    // await rest.put(
    //   Routes.applicationGuildCommands(client.user.id, process.env.GUILD_ID), // GUILD_ID will need to be in .env
    //   { body: commands },
    // );
    // For global commands (can take up to an hour to propagate)
    await rest.put(
      Routes.applicationCommands(client.user.id),
      { body: commands },
    );
    console.log('Successfully reloaded application (/) commands.');
  } catch (error) {
    console.error(error);
  }
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  const { commandName } = interaction;

  if (commandName === 'ping') {
    await interaction.reply('Pong!');
  }
});

client.on('voiceStateUpdate', async (oldState, newState) => {
  const member = newState.member || oldState.member;
  if (!member || member.user.bot) return;

  // Ensure the recordings directory exists
  const recordingsDir = path.join(__dirname, 'data', 'recordings');
  if (!fs.existsSync(recordingsDir)) {
    fs.mkdirSync(recordingsDir, { recursive: true });
    console.log(`Created directory: ${recordingsDir}`);
  }

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

