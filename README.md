# DiscordvoiceAI

このプロジェクトは、指定したボイスチャンネルでの会話を録音し、ローカルの `faster-whisper` で文字起こしした後、Gemini API を用いて整形する Discord Bot の簡易実装です。

## 必要条件

- Node.js 18 以上
- FFmpeg

## セットアップ手順

1. リポジトリを任意のフォルダーにクローンまたはコピーします。
2. プロジェクトルートで `npm install` を実行して Node.js の依存パッケージを取得します。
3. `pip install -r requirements.txt` を実行して Python 側のライブラリをインストールします。
4. プロジェクトルートに `.env` ファイルを作成します。
   起動時に `.env` が存在しない場合、設定例を記載した `.env.example` が自動生成されます。
   以下の内容を参考に `.env` を作成してください。
   ```
   DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   TRANSCRIPTION_MODEL="small"     # 任意
   GEMINI_MODEL="gemini-2.5-flash" # 任意
   TEST_GUILD_ID="YOUR_TEST_GUILD_ID" # 任意: スラッシュコマンドを即時反映させたいテストサーバーID
   ```
5. Bot を起動します。データディレクトリ(`data/recordings`) は起動時に自動で作成されます。
   ```bash
   node index.js
   ```
## スラッシュコマンド

現在、以下の基本的なスラッシュコマンドが実装されています。

-   `/ping`: ボットがオンラインであるかを確認します。"Pong!" と応答します。

### 新しいスラッシュコマンドの追加方法 (開発者向け)

1.  **コマンド定義**: `index.js` ファイル内の `commands` 配列に新しいコマンド定義を追加します。`SlashCommandBuilder` を使用してコマンド名、説明、オプションなどを設定します。
    ```javascript
    // 例:
    // const commands = [
    //   new SlashCommandBuilder().setName('ping').setDescription('Replies with Pong!'),
    //   new SlashCommandBuilder().setName('hello').setDescription('Greets the user.').addUserOption(option => option.setName('user').setDescription('The user to greet')),
    // ].map(command => command.toJSON());
    ```
2.  **コマンド登録**: コマンド定義はボット起動時に `client.once('ready', ...)` 内の処理で自動的に Discord に登録されます。
    *   開発中は、`.env` ファイルに `GUILD_ID` (READMEでは `TEST_GUILD_ID` と記載されているものと同じ) を設定し、`index.js` 内のギルドコマンド登録部分 (`Routes.applicationGuildCommands(...)`) のコメントを解除すると、特定のサーバーでコマンドが即座に反映されるため便利です。グローバルコマンド (`Routes.applicationCommands(...)`) は反映に最大1時間かかることがあります。
3.  **インタラクション処理**: `index.js` ファイル内の `client.on('interactionCreate', ...)` イベントリスナーに、新しいコマンドの処理ロジックを追加します。
    ```javascript
    // client.on('interactionCreate', async interaction => {
    //   if (!interaction.isChatInputCommand()) return;
    //   const { commandName, options } = interaction;

    //   if (commandName === 'ping') {
    //     await interaction.reply('Pong!');
    //   } else if (commandName === 'hello') {
    //     const user = options.getUser('user');
    //     await interaction.reply(user ? `Hello, ${user.username}!` : 'Hello there!');
    //   }
    // });
    ```

## 仕組みの概要

- 音声データは `data/recordings` ディレクトリに一時保存されます。このディレクトリはボット起動時に自動的に作成されます。
- チャンクごとに生成された WAV ファイルは `faster-whisper` で文字起こしを行います。
- 文字起こし結果は Gemini API で整形され、指定したチャンネルへ送信されます。

## ライセンス

MIT

## 実行方法 (discord.js v14)

1. ルートディレクトリで `npm install` を実行し依存パッケージを取得します。
2. `.env` に `DISCORD_TOKEN` と各 API キーを設定します。
3. `node index.js` を実行すると Bot が起動します。

録音ファイルは `data/recordings` に保存され、`faster-whisper` で文字起こしされます。
