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
## 仕組みの概要

- 音声データは `data/recordings` ディレクトリに一時保存されます。
- チャンクごとに生成された WAV ファイルは `faster-whisper` で文字起こしを行います。
- 文字起こし結果は Gemini API で整形され、指定したチャンネルへ送信されます。

## ライセンス

MIT

## 実行方法 (discord.js v14)

1. ルートディレクトリで `npm install` を実行し依存パッケージを取得します。
2. `.env` に `DISCORD_TOKEN` と各 API キーを設定します。
3. `node index.js` を実行すると Bot が起動します。

録音ファイルは `data/recordings` に保存され、`faster-whisper` で文字起こしされます。
