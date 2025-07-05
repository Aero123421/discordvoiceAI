# DiscordvoiceAI

このプロジェクトは、指定したボイスチャンネルでの会話を録音し、`faster-whisper`で文字起こしした後、Gemini API を用いて整形する Discord Bot の簡易実装です。

## 必要条件

- Python 3.9 以上
- FFmpeg

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
4. プロジェクトルートに `.env` ファイルを作成し、次の内容を設定します。
   ```
   DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
   TRANSCRIPTION_MODEL="small"     # 任意
   GEMINI_MODEL="gemini-2.5-flash" # 任意
   ```
5. Bot を起動します。
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
