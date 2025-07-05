# DiscordvoiceAI

このプロジェクトは、指定したボイスチャンネルでの会話を録音し、`faster-whisper`で文字起こしした後、Gemini API を用いて整形する Discord Bot の簡易実装です。

## 必要条件

- Python 3.9 以上
- FFmpeg
- PyNaCl

## セットアップ手順

1. リポジトリを任意のフォルダーにクローンまたはコピーします。
2. ターミナル（PowerShell など）でプロジェクトルートに移動し、仮想環境を作成して有効化します。
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows の場合
   # または
   source venv/bin/activate   # Unix 系の場合
   ```
3. 依存ライブラリをインストールします。
   ```bash
   pip install -r requirements.txt
   ```
   **注意**: `discord` パッケージではなく、Pycord (`py-cord`) を使用します。誤って
   `discord.py` や `discord` をインストールしていると、`discord.Bot` が
   見つからないエラーが発生します。また、ボイス機能には `PyNaCl` のインストールが
   必須です。
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
5. Bot を起動します。データディレクトリ(`data/queue`, `data/recordings`) は起動時に自動で作成されます。
   ```bash
   python main.py
   ```
6. Discord 上で `/setup channels` コマンドを実行し、録音対象のカテゴリと結果送信先のテキストチャンネルを選択します。

## 仕組みの概要

- 音声データは `data/recordings` ディレクトリに一時保存されます。
- チャンクごとに生成された WAV ファイルはバックグラウンドワーカーが取得し、`faster-whisper` で文字起こしを行います。
- 文字起こし結果は Gemini API で整形され、指定したチャンネルへ送信されます。

## ライセンス

MIT

## Node.js 版 (discord.js v14)

Node.js 18 以上がインストールされていれば、`discord.js` を利用した Bot も起動できます。

1. ルートディレクトリで `npm install` を実行し依存パッケージを取得します。
2. `.env` に `DISCORD_TOKEN` を設定します。
3. `node index.js` を実行すると Bot が起動します。

録音ファイルは `data/recordings` に保存され、`transcriber.py` 経由で文字起こしされます。
