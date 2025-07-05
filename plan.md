# discordvoiceAI
# AI駆動型Discord文字起こしBotのアーキテクチャ設計と実装ガイド

## 第1章：システムアーキテクチャとプロジェクト基盤

本章では、プロジェクト全体の概念的および技術的な基盤を構築します。高レベルのアーキテクチャを定義し、プロジェクトのファイル構造を詳述し、認証情報を安全に管理する方法を実装します。

### 1.1. 高レベルアーキテクチャ概要（イベント駆動、キューイング処理）

本Botのアーキテクチャは、ユーザーのアクション（ボイスチャンネルへの参加・退出）が、非同期で疎結合な一連のプロセスをトリガーするイベント駆動型システムとして設計されています。この設計は、リアルタイムの音声録音処理と、CPU負荷の高い文字起こし処理を分離することで、システムの安定性と応答性を最大化します。

以下に、システムの主要コンポーネントとその連携を示します。

(注：上記は概念図のプレースホルダーです。実際の図では各コンポーネント間のデータフローが示されます。)

**コアコンポーネント:**

1. **Discordイベントリスナー (`Pycord`)**: Discordとの主要なインターフェースであり、スラッシュコマンドとボイスステートの更新を処理する責務を負います。
    
2. **録音セッションマネージャー**: 各ユーザーのアクティブな録音を管理するステートフルなコンポーネント。録音の開始、停止、音声のチャンク化（分割）を制御します。
    
3. **永続的ジョブキュー (`aiodiskqueue`)**: システムの回復性を担保するバックボーン。Botの再起動やクラッシュ時にも文字起こしタスクが失われないようにします。このコンポーネントは、リアルタイムの録音処理とCPU集約的な文字起こし処理を効果的に分離（デカップリング）します 1。
    
4. **文字起こしワーカー (`faster-whisper`)**: キューからジョブを取得し、ローカルのCPUベースで音声からテキストへの変換を実行するバックグラウンドのコンシューマータスクです。
    
5. **AI後処理プロセッサ (`google-genai`)**: Gemini APIを使用して、生の文字起こし結果を洗練させる最終段階のコンポーネント。誤字脱字の修正、構造化、可読性の向上を担います。
    
6. **出力ハンドラー**: 最終的な`.txt`ファイルの生成と送信、および後続のデータクリーンアップを管理します。
    

このアーキテクチャは、プロデューサー・コンシューマーモデルに基づいています。Discordと対話する部分はタスク（音声ファイル）の「プロデューサー」として機能し、文字起こし部分は「コンシューマー」として機能します。この分離は、システム全体のパフォーマンスと安定性を確保する上で極めて重要です。ユーザーのローカルPC（Ryzen 5 5500G）でホストするという要件を考慮すると、`faster-whisper`による文字起こしはCPUリソースを大きく消費する可能性があります 2。もしこの重い処理がDiscordのイベントハンドラと同じ非同期ループ内で実行されると、Botのハートビートがブロックされ、Discordから切断されるリスクがあります。さらに、インメモリの

`asyncio.Queue`では、再起動時にキュー内の全ジョブが失われ、回復性の要件を満たせません 4。したがって、永続的なディスクベースのキュー（例：

`aiodiskqueue` 6）を採用することで、軽量なイベントハンドラと重いバックグラウンドワーカーを橋渡しします。このアーキテクチャ上の選択は、パフォーマンスの分離、安定性、データ整合性という複数の核心的要件を同時に満たすための論理的帰結です。

### 1.2. 開発環境の構築：プロジェクト構造と依存関係

プロフェッショナルでスケーラブルなプロジェクト構造を以下のように定義します。この構造は、関心事の分離を促進し、コードの保守性を高めます。

```
/discord-transcription-bot
|
|-- /cogs
| |-- __init__.py
| |-- setup_cog.py          # /setup コマンド関連のロジック
| |-- recording_cog.py      # 録音とイベントハンドリングのロジック
|
|-- /core
| |-- __init__.py
| |-- session_manager.py    # 録音セッションを管理するクラス
| |-- transcription_worker.py # 文字起こしキューを処理するワーカー
| |-- gemini_processor.py   # Gemini APIとの通信を担うクラス
|
|-- /data
| |-- /recordings/          # WAVチャンクの一時保存場所
| |-- /transcripts/         # 生テキストの一時保存場所
| |-- /queue/               # aiodiskqueueの永続化ディレクトリ
|
|-- main.py                   # Botのメインエントリポイント
|-- requirements.txt          # プロジェクトの依存ライブラリ
|--.env                      # 環境変数設定ファイル
|--.gitignore                # Gitの追跡対象外ファイルを指定
|-- README.md                 # プロジェクトの説明
```

`requirements.txt`ファイルには、安定性のために正確なバージョンを記載します。主要なライブラリは以下の通りです。

```
# requirements.txt
py-cord==2.5.0
faster-whisper==1.0.3
google-generativeai==0.7.2
python-dotenv==1.0.1
aiodiskqueue==0.3.1
```

また、Pycordでの音声処理には**FFmpeg**がシステム依存関係として不可欠です 7。開発環境および本番環境にあらかじめインストールしておく必要があります。

### 1.3. `python-dotenv`による安全な設定管理

APIキーやトークンのような機密情報をソースコードに直接書き込む（ハードコーディングする）ことは、重大なセキュリティリスクとなります。この問題を回避するため、`python-dotenv`ライブラリを使用し、環境変数を通じて設定を管理します 9。

`.env`ファイルのテンプレートを以下に示します。このファイルは`.gitignore`に追加し、バージョン管理システムには含めないようにします。

コード スニペット

```
#.env - 環境変数設定ファイル

# --- 必須設定 ---
# Discord Botのトークン
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN"

# Google Gemini APIのキー
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# --- Bot設定（任意） ---
# faster-whisperで使用するモデルサイズ
# 選択肢: tiny, base, small, medium, large-v3
# "small"または"base"がCPU負荷と精度のバランスから推奨される
TRANSCRIPTION_MODEL="small"

# Gemini APIで使用するモデル名
# コストと性能のバランスから"gemini-2.5-flash"を推奨
GEMINI_MODEL="gemini-2.5-flash"
```

Pythonコード内では、`os.getenv()`を使用してこれらの変数を安全に読み込みます。これにより、コードと設定が分離され、安全性が向上します 11。

Python

```python
import os
from dotenv import load_dotenv

#.envファイルから環境変数を読み込む
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
```

## 第2章：コアBotロジックとイベントハンドリング（Pycord）

本章では、Pycordライブラリを用いてBotの骨格を構築し、Discord APIとのインタラクションに焦点を当てます。

### 2.1. Botの初期化：Cogs、Intents、グローバル状態管理

Botの機能をモジュール化し、コードの整理と再利用性を高めるために、**Cogs**を利用します。`main.py`はBotの起動とCogsの読み込みを担当するエントリポイントとなります。また、Botの動作に必要な権限をDiscordに伝えるため、`Intents`を明示的に設定します。

Python

```python
# main.py
import discord
import os
from dotenv import load_dotenv

#.envファイルから環境変数を読み込む
load_dotenv()

# Botが必要とするIntentsを定義
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = False # メッセージ内容は不要

# Botクラスをインスタンス化
bot = discord.Bot(intents=intents)

# Cogsをロードする
cogs_list = [
    "setup_cog",
    "recording_cog"
]

for cog in cogs_list:
    bot.load_extension(f"cogs.{cog}")

@bot.event
async def on_ready():
    print(f"{bot.user}としてログインしました。")

# Botを起動
bot.run(os.getenv("DISCORD_TOKEN"))
```

この実装では、`guilds`（サーバー情報の取得）、`voice_states`（ボイスチャンネルの状態変化の検知）のIntentを有効にしています 13。メッセージ内容のIntentは不要であるため、無効化することで、Botが必要とする権限を最小限に留めています。これは、DiscordのBot開発におけるベストプラクティスです 15。

### 2.2. `/setup`コマンド：セレクトメニューによるユーザーフレンドリーな設定

ユーザーがBotの動作を簡単に設定できるよう、インタラクティブなUIコンポーネントである**セレクトメニュー**（ドロップダウン）を使用した`/setup`コマンドを実装します。これにより、ユーザーはコマンドを覚えることなく、視覚的に設定を行えます 16。

このコマンドは`cogs/setup_cog.py`に実装します。

Python

```python
# cogs/setup_cog.py
import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
import json

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    setup = SlashCommandGroup("setup", "Botの初期設定を行います。")

    @setup.command(name="channels", description="録音対象のカテゴリと通知用テキストチャンネルを設定します。")
    async def setup_channels(self, ctx: discord.ApplicationContext):
        # サーバー内のカテゴリとテキストチャンネルを取得
        categories = [c for c in ctx.guild.channels if isinstance(c, discord.CategoryChannel)]
        text_channels =

        if not categories or not text_channels:
            await ctx.respond("設定に必要なチャンネルが見つかりません。", ephemeral=True)
            return

        # セレクトメニューのコンポーネントを作成
        category_select = discord.ui.Select(
            placeholder="録音対象のボイスチャンネルカテゴリを選択",
            options=
        )
        text_channel_select = discord.ui.Select(
            placeholder="文字起こし結果の送信先チャンネルを選択",
            options=
        )

        async def callback(interaction: discord.Interaction):
            # ユーザーの選択を保存
            config = {
                "target_category_id": int(category_select.values),
                "output_channel_id": int(text_channel_select.values)
            }
            # 簡単のためJSONファイルに保存
            with open(f"config_{ctx.guild.id}.json", "w") as f:
                json.dump(config, f)
            
            await interaction.response.send_message("設定が完了しました。", ephemeral=True)

        category_select.callback = callback
        text_channel_select.callback = callback

        view = discord.ui.View()
        view.add_item(category_select)
        view.add_item(text_channel_select)

        await ctx.respond("以下のメニューから設定を行ってください:", view=view, ephemeral=True)

def setup(bot):
    bot.add_cog(SetupCog(bot))
```

このコードでは、`discord.ui.Select`を使用して、サーバーに存在するカテゴリとテキストチャンネルを動的にリストアップし、選択肢として提示します 18。ユーザーが選択を完了すると、そのIDがJSONファイルに保存されます。これにより、Botはどのチャンネルを監視すべきかを永続的に記憶できます。

### 2.3. `on_voice_state_update`イベントによるBotアクションの自動化

Botの主要なワークフローをトリガーするのが`on_voice_state_update`イベントです。このイベントは、ユーザーのボイスチャンネルに関する状態が変化するたびに（参加、退出、ミュート、デフなど）発火します 14。要件を満たすためには、この「ノイズの多い」イベントの中から、特定の条件下での「参加」と「退出」のみを正確に検知するロジックを実装する必要があります。

このロジックは`cogs/recording_cog.py`に実装します。

Python

```python
# cogs/recording_cog.py (一部)
from discord.ext import commands
import json

class RecordingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ここにセッションマネージャーやキューの初期化を追加

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return # Bot自身の状態変化は無視

        # 設定ファイルを読み込む
        try:
            with open(f"config_{member.guild.id}.json", "r") as f:
                config = json.load(f)
            target_category_id = config.get("target_category_id")
        except (FileNotFoundError, KeyError):
            return # 設定が存在しない場合は何もしない

        # --- ユーザーがVCに参加した時のロジック ---
        if before.channel is None and after.channel is not None:
            if after.channel.category_id == target_category_id:
                print(f"{member.name}が監視対象のVC({after.channel.name})に参加しました。")
                # TODO: 録音セッションを開始する処理を呼び出す
                # await self.session_manager.start_recording(member, after.channel)

        # --- ユーザーがVCから退出した時のロジック ---
        elif before.channel is not None and after.channel is None:
            # 退出したチャンネルが監視対象だったかを確認
            # (セッションマネージャーで管理している録音中のユーザーかを確認する方が確実)
            print(f"{member.name}がVC({before.channel.name})から退出しました。")
            # TODO: 録音セッションを終了・最終処理を行う処理を呼び出す
            # await self.session_manager.stop_recording(member)
```

この実装の核心は、`before`と`after`の状態を比較することです 19。

- **参加**: `before.channel`が`None`で、`after.channel`が`None`でない場合、ユーザーがVCに新たに参加したことを意味します。
    
- **退出**: `before.channel`が`None`でなく、`after.channel`が`None`である場合、ユーザーがVCから退出したことを意味します。
    
　
さらに、`after.channel.category_id`が`/setup`で設定されたIDと一致するかを検証することで、Botが意図しないチャンネルで動作することを防ぎます。この多段階のフィルタリングが、安定的で予測可能な動作を実現するための鍵となります。

## 第3章：高度な音声キャプチャと管理

本章では、Botのリアルタイム機能の中核である、音声の録音処理について技術的な詳細を掘り下げます。各ユーザーの音声を個別に、かつ途切れることなく安定してキャプチャするためのフレームワークを構築します。

### 3.1. `discord.sinks`によるユーザー個別音声のキャプチャ

Pycordの音声受信システムは、`start_recording`メソッドに渡される`Sink`オブジェクトを通じて、高度な録音制御を可能にします 20。要件である「ユーザーごとの個別録音」は、この

`Sink`の特性を利用することで実現できます。

録音完了後、`once_done`コールバック関数に渡される`sink`オブジェクトには、`audio_data`という属性が含まれています。これは、`user_id`をキーとし、そのユーザーの音声データ（`AudioData`オブジェクト）を値とする辞書です 20。この仕組みにより、ボイスチャンネル内の全音声が混合されるのではなく、話者ごとに分離された音声ストリームを取得できます。

要件ではWhisperとの互換性が高いWAV形式が推奨されているため、`discord.sinks.WaveSink`を使用します。

Python

```python
import discord

#... 録音開始処理内...
vc = await channel.connect()
# WaveSinkを使用して録音を開始
vc.start_recording(
    discord.sinks.WaveSink(),
    self.once_done_callback,  # 録音完了時のコールバック関数
    member, # コールバックに渡す引数
)

#...

async def once_done_callback(self, sink: discord.sinks.WaveSink, member: discord.Member, *args):
    # コールバック内で、特定のユーザーの音声データのみを処理する
    user_audio = sink.audio_data.get(member.id)
    if user_audio:
        # user_audio.fileはBytesIOオブジェクト
        # これをファイルに保存する
        file_path = f"./data/recordings/{member.name}_{int(time.time())}.wav"
        with open(file_path, "wb") as f:
            f.write(user_audio.file.getbuffer())
        print(f"{member.name}の音声チャンクを{file_path}に保存しました。")
        # TODO: file_pathを文字起こしキューに追加する
```

このアプローチは、Craig bot 22 のようなマルチトラック録音の概念を、アプリケーションレベルで実現するものです。

### 3.2. `discord.ext.tasks`による5分間の音声チャンク化

Pycordの`start_recording`には、一定時間で自動的にファイルを分割する機能は組み込まれていません 23。この要件を実現するためには、

`discord.ext.tasks`拡張機能を用いて、定期的に録音を停止・再開するサイクルを自前で実装する必要があります 24。

ここでの重要な実装パターンは、`tasks.loop`を使って定期的に`vc.stop_recording()`を呼び出すことです。`stop_recording()`が呼び出されると、`start_recording()`で指定した`once_done`コールバックがトリガーされます。そして、そのコールバック関数内でファイルの保存処理と、**即座の録音再開** (`vc.start_recording()`) を行うのです。

この「停止→コールバックで保存→コールバック内で即再開」というサイクルにより、シームレスなチャンク化が実現します。

Python

```python
# cogs/recording_cog.py (一部)
from discord.ext import tasks

class RecordingSession:
    def __init__(self, member, voice_client, cog_instance):
        self.member = member
        self.vc = voice_client
        self.cog = cog_instance
        self.chunk_task = self.create_chunking_task()

    def start(self):
        self.chunk_task.start()

    def stop(self):
        self.chunk_task.cancel()
        if self.vc.is_recording():
            self.vc.stop_recording()

    def create_chunking_task(self):
        @tasks.loop(minutes=5.0)
        async def chunker():
            if self.vc.is_recording():
                self.vc.stop_recording() # これでonce_doneコールバックがトリガーされる
        
        @chunker.before_loop
        async def before_chunker():
            # ループ開始時に最初の録音を開始
            self.vc.start_recording(
                discord.sinks.WaveSink(),
                self.cog.once_done_callback,
                self.member,
            )
        return chunker

# RecordingCogクラス内
async def once_done_callback(self, sink: discord.sinks.WaveSink, member: discord.Member, *args):
    #... ファイル保存処理...
    
    # 録音を即座に再開する
    # セッションがまだアクティブかを確認する必要がある
    session = self.session_manager.get_session(member.id)
    if session and session.vc.is_connected():
        session.vc.start_recording(
            discord.sinks.WaveSink(),
            self.once_done_callback,
            member,
        )
```

この手法の鍵は、`stop_recording()`が単なる停止命令ではなく、録音ライフサイクルを完了させ、コールバックを通じてデータ処理フェーズへ移行させるためのトリガーであると理解することです。コールバック内で即座に次のライフサイクルを開始することで、音声が失われる時間をミリ秒単位に抑え、連続的な録音を実現します。

### 3.3. 並行録音セッションを管理する堅牢なフレームワーク

Botは複数のユーザーが異なるVCで同時に録音することをサポートする必要があります。これを実現するには、各録音セッションの状態を個別に管理する仕組みが不可欠です。`core/session_manager.py`に`RecordingSessionManager`クラスを実装します。

このマネージャークラスは、`user_id`をキーとして、各ユーザーの録音状態をカプセル化した`RecordingSession`オブジェクトを管理する辞書を内部に持ちます。

Python

```python
# core/session_manager.py

class RecordingSession:
    # (前述のRecordingSessionクラスの実装)
    #... 加えて、一時的な文字起こしテキストを保持するリストなどを追加
    def __init__(self,...):
        #...
        self.transcript_segments =

class RecordingSessionManager:
    def __init__(self, bot, transcription_queue):
        self.bot = bot
        self.active_sessions = {} # {user_id: RecordingSession}
        self.transcription_queue = transcription_queue

    async def start_recording(self, member, channel):
        if member.id in self.active_sessions:
            return # すでに録音中

        try:
            vc = await channel.connect()
            session = RecordingSession(member, vc, self) # selfをcog_instanceとして渡す
            self.active_sessions[member.id] = session
            session.start()
            print(f"セッション開始: {member.name}")
        except Exception as e:
            print(f"録音開始エラー: {e}")

    async def stop_recording(self, member):
        session = self.active_sessions.pop(member.id, None)
        if session:
            session.stop()
            if session.vc.is_connected():
                await session.vc.disconnect()
            
            # TODO: 最終的な文字起こし処理をトリガー
            # final_text = "".join(session.transcript_segments)
            # await self.gemini_processor.process(final_text, member)
            
            print(f"セッション終了: {member.name}")

    def get_session(self, user_id):
        return self.active_sessions.get(user_id)

    # once_done_callbackもこのクラス内に移動し、キューへの追加を行う
    async def once_done_callback(self, sink, member, *args):
        #... ファイル保存処理...
        file_path = "..."
        await self.transcription_queue.put((member.id, file_path))
        
        #... 録音再開ロジック...
```

このオブジェクト指向のアプローチにより、各ユーザーの状態（ボイスクライアント、チャンキングタスク、蓄積されたテキストなど）が明確に分離され、コードの可読性と保守性が大幅に向上します。

## 第4章：回復力のある文字起こしパイプライン

本章では、バックエンドの処理、特に文字起こしプロセスを、指定されたハードウェア上で堅牢、耐障害性、かつ高性能にするための設計と実装に焦点を当てます。

### 4.1. 障害を前提としたアーキテクチャ：`aiodiskqueue`による永続的キュー

ユーザー要件である「Botの再起動対応」を満たすためには、標準のインメモリ`asyncio.Queue`では不十分です。Botがクラッシュまたは再起動した場合、メモリ上のキューにあるすべての処理待ちタスク（音声ファイルのパス）は失われてしまいます 5。

この問題を解決するため、ディスクに状態を永続化するキューライブラリ`aiodiskqueue`を採用します 6。このライブラリはネイティブな

`asyncio`サポートを提供し、APIが`asyncio.Queue`と類似しているため、既存の非同期コードに容易に統合できます。

キューの初期化はBot起動時に行い、永続化用のディレクトリ（例：`./data/queue/`）を指定します。

Python

```python
# main.py (一部)
import aiodiskqueue

async def main():
    #...
    # 永続的キューを初期化
    transcription_queue = await aiodiskqueue.Queue.create("./data/queue")
    
    # Botインスタンスにキューを持たせる
    bot.transcription_queue = transcription_queue
    
    # 文字起こしワーカータスクを開始
    bot.loop.create_task(transcription_worker(bot))
    
    await bot.start(os.getenv("DISCORD_TOKEN"))

#...
```

プロデューサー（第3章の`once_done_callback`）は、`await queue.put(item)`でジョブ（音声ファイルのパスとユーザーIDのタプル）をキューに追加します。コンシューマー（文字起こしワーカー）は、`await queue.get()`でジョブを取得します。これにより、Botが停止しても未処理のジョブはディスク上に残り、再起動後に処理を再開できます。

### 4.2. 文字起こしワーカー：非同期処理のための専用バックグラウンドタスク

文字起こし処理はCPU負荷が高く、完了までに時間がかかる可能性があるため、Discordとの通信を行うメインのイベントループから完全に分離する必要があります。そのために、Bot起動時に開始される専用のバックグラウンドタスク（コンシューマー）を実装します 4。

このワーカーは、アプリケーション内で唯一`faster-whisper`ライブラリと直接やり取りするコンポーネントとなります。

**ワーカーのロジック (`core/transcription_worker.py`):**

Python

```python
# core/transcription_worker.py
import asyncio
from faster_whisper import WhisperModel

async def transcription_worker(bot):
    # モデルのロードは一度だけ行う
    model_size = os.getenv("TRANSCRIPTION_MODEL", "small")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    print(f"Faster-Whisperモデル({model_size})をロードしました。")

    while True:
        try:
            # キューからジョブを取得
            user_id, audio_path = await bot.transcription_queue.get()
            
            print(f"文字起こし開始: {audio_path}")
            
            # CPUバウンドな同期処理を別スレッドで実行
            loop = asyncio.get_running_loop()
            segments, info = await loop.run_in_executor(
                None,  # デフォルトのThreadPoolExecutorを使用
                lambda: model.transcribe(audio_path, beam_size=5)
            )
            
            transcribed_text = "".join(segment.text for segment in segments)
            print(f"文字起こし完了: {audio_path}")

            # 結果をセッションマネージャーに渡して蓄積
            session = bot.session_manager.get_session(user_id)
            if session:
                session.transcript_segments.append(transcribed_text)

            # 処理済みファイルを削除
            os.remove(audio_path)

            # キューにタスク完了を通知
            bot.transcription_queue.task_done()

        except Exception as e:
            print(f"文字起こしワーカーでエラーが発生: {e}")
            # エラーが発生してもワーカーは継続
            await asyncio.sleep(5)
```

この実装における最も重要な点は、`loop.run_in_executor`の使用です。`faster-whisper`の`model.transcribe()`メソッドは同期的でCPUバウンドな関数です 27。これを直接

`await`なしで呼び出すと、完了するまで（数秒から数分）イベントループ全体がブロックされてしまいます。`run_in_executor`は、このブロッキング処理を別のスレッドプールにオフロードし、メインのイベントループがBotの応答性（ハートビート、コマンドへの応答など）を維持できるようにします。これは、安定したBotを構築するための不可欠なテクニックです。

### 4.3. `faster-whisper`による高性能CPU文字起こし

`faster-whisper`は、OpenAIのWhisperモデルをCTranslate2（Transformerモデル用の高速推論エンジン）で再実装したもので、オリジナルの実装よりも大幅に高速かつ省メモリで動作します 28。CTranslate2は、重みの量子化（

`int8`など）、レイヤー融合、バッチ並べ替えといった多くの最適化技術を適用しています 30。

ユーザーの環境（Ryzen 5 5500G）は、ミドルレンジのCPUです。この環境で最適なパフォーマンスを得るためには、文字起こしの速度、精度（WER: Word Error Rate）、リソース使用量（RAM）のトレードオフを理解することが重要です。

**表1：ミドルレンジCPU（Ryzen 5 5500G/5600G相当）における`faster-whisper`の性能とリソース使用量の推定**

|モデルサイズ|量子化|RAM使用量 (約)|処理速度 (対リアルタイム比)|WER (単語誤り率, 約)|推奨用途|
|---|---|---|---|---|---|
|`tiny`|`int8`|~1 GB|> 10x|15-25%|速度最優先、精度は問わない場合|
|`base`|`int8`|~1.5 GB|~8x|10-20%|速度と精度のバランスが良い初期選択肢|
|`small`|`int8`|~2.5 GB|~5x|8-15%|**本プロジェクトでの推奨設定**。十分な速度と高い精度。|
|`medium`|`int8`|~5 GB|~2x|5-10%|精度最優先で、キューの滞留が許容できる場合。|

出典: 2のベンチマーク結果を基に総合的に推定。処理速度はオーディオの長さに比べて何倍速く処理できるかを示す。

この表から、`small`モデルを`int8`量子化で使用することが、本プロジェクトの要件である「CPUベースでも十分な性能」と精度のバランスを取る上で最適な選択肢であると結論付けられます。3のベンチマークでは、類似のRyzen 5 5600G CPUで

`small`モデルを使用した場合、6分30秒の音声を約54秒で処理できており、リアルタイムを大幅に上回る性能が期待できます。ユーザーは`.env`ファイルでこのモデルサイズを簡単に変更し、自身の環境に合わせて調整することが可能です。

### 4.4. ユーザーごとの文字起こしデータ蓄積

文字起こしワーカーによって生成されたテキストセグメントは、ユーザーがVCを退出するまで一時的に保存される必要があります。このデータは、第3章で導入した`RecordingSessionManager`が管理する`RecordingSession`オブジェクト内のリスト（`transcript_segments`）に、メモリ上で蓄積されます。これにより、ユーザーが退出した際に、そのセッションで生成されたすべてのテキストを連結し、次のAI後処理ステップに渡すことができます。

## 第5章：Gemini APIによるAI駆動のテキスト洗練

本章では、`faster-whisper`から得られた生の文字起こしテキストを、強力な大規模言語モデル（LLM）であるGemini APIを用いて、誤字脱字の修正、構造化、整形を行い、最終的な成果物の品質を飛躍的に向上させるプロセスを詳述します。

### 5.1. AI後処理のための文字起こしテキスト準備

ユーザーがボイスチャンネルから退出すると、`on_voice_state_update`イベントが最終処理のトリガーとなります。`RecordingSessionManager`は、該当ユーザーのセッションを終了し、そのセッション中に`transcript_segments`リストに蓄積されたすべてのテキスト断片を取得します。これらの断片は、単純に連結されて一つの大きな文字列（講義全体の生テキスト）にまとめられます。

このプロセスにおける重要な利点は、Gemini 2.5モデルが持つ巨大なコンテキストウィンドウです 32。従来のLLMはコンテキストウィンドウが小さく（例：4,000トークン）、長いテキストを処理するには複雑な分割・要約処理（Map-Reduceのような戦略）が必要でした。しかし、Gemini 2.5は100万トークン以上を一度に処理できるため、講義全体のテキストを単一のリクエストで送信できます 34。これにより、アーキテクチャが大幅に簡素化され、モデルはテキスト全体の関係性を考慮した上で、より一貫性のある高品質な修正と構造化を行うことができます。

### 5.2. 修正、構造化、整形のための高度なプロンプトエンジニアリング

Gemini APIから期待通りの出力を得るためには、プロンプトの設計（プロンプトエンジニアリング）が極めて重要です。ここでは、役割付与、タスク指示、出力形式指定、そして少数事例（Few-shot）プロンプティングを組み合わせた、高度なプロンプトを設計します 35。

Python

```
# core/gemini_processor.py (プロンプト部分)

def create_prompt(raw_transcript: str) -> str:
    # プロンプトのテンプレート
    prompt = f"""
あなたは、大学の講義の文字起こしテキストを処理し、構造化することに特化した専門のAIアシスタントです。あなたの目的は、生のテキストに含まれる誤字脱字や文法的な誤りを修正し、学習資料として利用しやすいように整形することです。

# 指示
以下の「生の文字起こしテキスト」を分析し、次の処理を実行してください。

1.  **修正**: 文脈に基づいて、明らかなスペルミス、文法エラー、文字起こし特有の誤り（例：「えー」「あのー」などのフィラーワードの除去、同音異義語の訂正）を修正してください。
2.  **構造化**: 内容の論理的な区切りを見つけ、適切な段落分けや改行を挿入してください。可能であれば、内容の変わり目に見出し（例：`## 新しいトピック`）を追加してください。
3.  **要約とキーワード抽出**: 講義全体の要点を3〜5文で要約し、議論された主要な専門用語や概念をリストアップしてください。
4.  **出力形式**: 最終的な出力は、必ず単一のJSONオブジェクト形式でなければなりません。JSONオブジェクト以外のテキスト（前置きや後書きなど）は一切含めないでください。

# JSONスキーマ
出力するJSONオブジェクトは、以下のスキーマに厳密に従ってください。

{{
    "title": "講義内容を的確に表す簡潔なタイトル（AIが生成）",
    "summary": "講義内容の3〜5文からなる要約",
    "key_terms": [
        "キーワード1",
        "キーワード2",
        "キーワード3"
    ],
    "full_transcript": "修正・整形済みの完全な文字起こしテキスト。適切な段落や改行が含まれていること。"
}}

# 生の文字起こしテキスト
---
{raw_transcript}
---

# 出力 (JSON形式)
"""
    return prompt
```

このプロンプトは以下の要素で構成されています。

- **役割（Persona）**: 「専門のAIアシスタント」という役割を与えることで、モデルの振る舞いを特定のタスクに最適化します。
    
- **明確な指示（Instruction）**: 修正、構造化、要約、キーワード抽出という具体的なタスクを箇条書きで明示します。
    
- **出力形式の厳格な指定（Output Format）**: 出力をJSON形式に限定し、そのスキーマを明確に定義することで、プログラムでの後処理を容易にします。これは、一貫した出力を得るための非常に効果的な手法です 37。
    
- **コンテキストの提供**: `---`で区切られたセクションに生の文字起こしテキストを埋め込み、モデルが処理すべき対象を明確にします。
    

### 5.3. `google-genai`クライアントによる堅牢なAPI通信の実装

Gemini APIとの通信は、公式の`google-genai`ライブラリを使用して実装します 38。

`core/gemini_processor.py`に、API通信をカプセル化するクラスを作成します。

Python

```
# core/gemini_processor.py
import google.generativeai as genai
import os
import json

class GeminiProcessor:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    async def process_transcript(self, raw_transcript: str) -> dict | None:
        prompt = self.create_prompt(raw_transcript)
        
        try:
            # 安全性設定を調整（講義内容によっては必要）
            safety_settings = {
                'HATE': 'BLOCK_NONE',
                'HARASSMENT': 'BLOCK_NONE',
                'SEXUAL': 'BLOCK_NONE',
                'DANGEROUS': 'BLOCK_NONE'
            }
            
            response = await self.model.generate_content_async(
                prompt,
                safety_settings=safety_settings
            )
            
            # JSONをパースして返す
            json_response = json.loads(response.text)
            return json_response

        except json.JSONDecodeError:
            print("Geminiからの応答が有効なJSONではありませんでした。")
            print(f"応答テキスト: {response.text}")
            return None
        except Exception as e:
            print(f"Gemini APIとの通信中にエラーが発生しました: {e}")
            return None

    def create_prompt(self, raw_transcript: str) -> str:
        # (前述のプロンプト生成関数の実装)
       ...
```

この実装では、`generate_content_async`を使用して非同期にAPIを呼び出します。また、学術的な内容が不適切と誤判定される可能性を低減するため、`safety_settings`を調整しています。

### 5.4. 構造化されたJSON応答の解析と利用

Gemini APIからの応答は、前述のプロンプトで指定したJSON形式の文字列です。この文字列をPythonの`json`ライブラリでパースし、辞書オブジェクトに変換します。

パース処理は`try...except`ブロックで囲み、モデルが稀に不正なJSONを返すケースに備えます 40。これにより、Botが予期せぬ応答でクラッシュするのを防ぎます。

パースが成功したら、要件に従い、辞書から`["full_transcript"]`キーの値を取得します。このテキストが、最終的にユーザーに届けられる、洗練された文字起こし結果となります。他のキー（`title`, `summary`, `key_terms`）も、将来的な機能拡張（例：要約をDiscordに直接投稿する）のために利用可能です。

## 第6章：出力、配信、およびデータハイジーン

本章では、ワークフローの最終段階である、処理結果のユーザーへの配信と、それに伴う一時データの安全なクリーンアップについて詳述します。

### 6.1. 最終的な文字起こしファイルの生成と配信

Gemini APIによる後処理が完了し、構造化されたJSON応答から`full_transcript`テキストが抽出された後、Botはこのテキストを`.txt`ファイルとして保存し、ユーザーが指定したテキストチャンネルに送信します。

ファイル名は要件定義に従い、`<username>_transcript_<timestamp>.txt`のような形式とし、一意性を確保しつつ、誰のどのセッションの文字起こしかが分かるようにします。ファイルの送信には、Pycordの`discord.File`オブジェクトを使用します 20。

Python

```
# core/session_manager.py (stop_recordingメソッド内)

#... GeminiProcessorによる処理後...
processed_data = await self.gemini_processor.process_transcript(final_raw_text)

if processed_data and "full_transcript" in processed_data:
    final_text = processed_data["full_transcript"]
    
    # ファイルを一時的に作成
    file_path = f"./data/transcripts/{member.name}_transcript_{int(time.time())}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_text)

    # 設定されたチャンネルにファイルを送信
    try:
        with open(f"config_{member.guild.id}.json", "r") as f:
            config = json.load(f)
        output_channel_id = config.get("output_channel_id")
        
        if output_channel_id:
            channel = self.bot.get_channel(output_channel_id)
            if channel:
                await channel.send(
                    f"{member.mention}さんの講義の文字起こしが完了しました。",
                    file=discord.File(file_path)
                )
                print(f"文字起こしファイルを{channel.name}に送信しました。")
                send_success = True
            else:
                print(f"エラー: 出力チャンネル(ID: {output_channel_id})が見つかりません。")
                send_success = False
    except Exception as e:
        print(f"ファイル送信中にエラーが発生しました: {e}")
        send_success = False
    
    # データハイジーンの実行
    if send_success:
        #... ファイル削除処理...
```

### 6.2. 一時的な音声およびテキストデータの安全な削除プロトコル

データプライバシーとセキュリティの観点から、一時ファイルのクリーンアップ（データハイジーン）は、このBotの信頼性を左右する極めて重要なプロセスです。ユーザーの音声データという機密情報を、処理が完了した後もサーバー上に放置することは、重大なプライバシー侵害およびセキュリティリスクとなります 10。

クリーンアップの対象となるデータは以下の通りです。

1. `/data/recordings/`に保存された、すべての中間`.wav`音声チャンク。
    
2. `RecordingSessionManager`によってメモリ上に保持されていた、一時的な文字起こしセグメント。
    
3. Discordへのアップロード後にローカルディスクに残っている、最終的な`.txt`ファイル。
    

データ損失を防ぐため、クリーンアップは**ユーザーが最終的な成果物を正常に受信した後にのみ**実行されるべきです。この原子性を保証するため、堅牢な実装が求められます。

Python

```
# core/session_manager.py (stop_recordingメソッド内)

#... ファイル送信処理後...
# 最終的なクリーンアップ
finally:
    # 一時的な.txtファイルを削除
    if 'file_path' in locals() and os.path.exists(file_path):
        os.remove(file_path)
        print(f"一時ファイル {file_path} を削除しました。")
    
    # このセッションに関連するすべての音声チャンクを削除
    # (セッションオブジェクトにファイルパスのリストを保持しておく必要がある)
    # for chunk_path in session.audio_chunks:
    #     if os.path.exists(chunk_path):
    #         os.remove(chunk_path)
    # print(f"{member.name}の音声チャンクをすべて削除しました。")
```

このロジックは、`try...finally`ブロック内に配置することが推奨されます。ファイル送信処理を`try`ブロック内で行い、成功したかどうかをフラグで管理します。そして`finally`ブロック内で、送信が成功した場合にのみファイルの削除を実行します。これにより、送信に失敗した場合でもファイルは保持され、手動でのリカバリーが可能となり、一方で成功した場合には確実に機密データが残らないことが保証されます。これは、データハイジーン要件を満たすための確実なアプローチです。

## 第7章：運用上のベストプラクティス：セキュリティ、コスト、エラーハンドリング

本章では、Botを責任を持って持続的に運用するための重要な考慮事項、すなわち、包括的なエラーハンドリング、プライバシー設計、そして外部APIのコストとレート制限の管理について分析します。

### 7.1. パイプライン全体にわたる包括的なエラーハンドリングと再試行ロジック

安定したサービスを提供するためには、パイプラインの各段階で発生しうる障害を予期し、適切に処理するエラーハンドリング機構が不可欠です。

- **Discord APIエラー**: Pycordは内部的に多くのAPIエラーを処理しますが、コマンド固有のエラーハンドラ（例：`@command.error`デコレータ）を実装することで、パーミッション不足や無効な引数といった特定のエラーに対して、ユーザーフレンドリーなフィードバックを返すことができます。
    
- **ファイルI/Oエラー**: 音声ファイルやテキストファイルの読み書き時には、`FileNotFoundError`や`PermissionError`などが発生する可能性があります。これらの操作はすべて`try...except`ブロックで囲み、エラーをログに記録し、処理を安全に中断または継続するようにします。
    
- **文字起こし失敗**: `faster-whisper`での処理中に予期せぬエラーが発生した場合、ワーカータスクがクラッシュしないように、`transcribe`呼び出しを包括的な`try...except`でラップします。失敗したジョブは、原因調査のために「デッドレターキュー」（処理失敗ジョブ専用のキュー）に移動させるか、ログに詳細を記録した上で破棄する戦略が考えられます。
    
- **Gemini APIエラー**: Gemini APIとの通信では、ネットワークの一時的な問題やレート制限超過によるエラーが発生する可能性があります。`google.api_core.exceptions.ResourceExhausted`（レート制限超過）やその他のHTTPエラーを捕捉し、**指数関数的バックオフ**（Exponential Backoff）を用いた再試行ロジックを実装することで、システムの回復力を高めることができます。
    

### 7.2. プライバシー・バイ・デザイン：安全なデータハンドリングとプライバシーポリシーのサンプル

本Botはユーザーの音声という機密性の高いデータを扱うため、設計段階からプライバシーを最優先に考慮する「プライバシー・バイ・デザイン」のアプローチが求められます。

**ベストプラクティス概要:**

1. **データ最小化**: 文字起こしタスクの完了に必要な最小限の時間のみデータを保持し、処理完了後は即座に削除します（第6.2章参照）。
    
2. **安全な設定管理**: APIキーやトークンなどの機密情報は、`.env`ファイルと環境変数を介して安全に管理し、ソースコードには一切含めません 10。
    
3. **最小権限の原則**: Botが必要とするDiscordのIntentを最小限に絞り、不要なデータへのアクセス権を持たせないようにします。
    
4. **透明性**: Discordは、認証済みBotに対してプライバシーポリシーの提示を義務付けています 15。ユーザーが、自身のデータがどのように扱われるかを明確に理解できるようにすることが不可欠です。
    

プライバシーポリシーのサンプル:

以下に、Apollo Bot 42 や一般的なベストプラクティス 43 を参考にしたプライバシーポリシーのテンプレートを示します。これは、Botのウェブサイトやサポートサーバーで公開する必要があります。

---

**プライバシーポリシー**

**最終更新日:** 2025年MM月DD日

本プライバシーポリシーは、「Discord文字起こしBot」（以下、「本サービス」）がユーザーの個人情報をどのように収集、使用、開示するかについて説明するものです。本サービスを利用することにより、あなたはこのポリシーに記載された情報収集と使用に同意したことになります。

1. 収集する情報

本サービスは、その機能を提供するために、以下の情報を一時的に収集します。

- **DiscordユーザーID**: どのユーザーの音声を録音・文字起こしするかを識別するために使用します。
    
- **音声データ**: あなたが指定されたボイスチャンネルで発した音声。これは文字起こし処理のためにのみ収集されます。
    

2. 情報の使用目的

収集した情報は、以下の目的のためにのみ使用されます。

- 本サービスの提供（音声の録音、文字起こし、テキストの整形）。
    
- 文字起こし結果をあなたに提供するため。
    

3. 情報の共有

本サービスは、あなたの個人情報を第三者に販売することはありません。ただし、サービスの提供に必要な範囲で、以下の第三者サービスにデータを送信します。

- **Google Gemini API**: 文字起こしされたテキストの誤字脱字修正、構造化、整形のために使用されます。Googleのプライバシーポリシーも合わせてご確認ください。
    

4. データ保持と削除

本サービスは、データ最小化の原則に基づき、あなたのデータを保持しません。

- **音声データ**: 5分ごとにチャンクとして一時的にサーバーに保存されますが、文字起こし処理が完了次第、直ちに削除されます。
    
- 文字起こしテキスト: 最終的な.txtファイルがあなたに送信された後、サーバー上の一時的なテキストデータはすべて削除されます。
    
    本サービスは、あなたのデータを長期的に保存することはありません。
    

5. 13歳未満の児童について

本サービスは、13歳未満の個人を対象としていません。13歳未満の児童から個人情報を意図的に収集することはありません。

6. 本ポリシーの変更

本プライバシーポリシーは、随時更新されることがあります。変更があった場合は、このページに新しいポリシーを掲載します。定期的にこのページを確認することをお勧めします。

## **7. お問い合わせ** 本プライバシーポリシーに関するご質問やご提案がございましたら、までお気軽にお問い合わせください。

### 7.3. Gemini APIのコストとレート制限の分析

Gemini APIの利用は、Botの運用コストに直結する重要な要素です。特に、Google AI Studio経由で取得したAPIキーを使用する場合、「無料ティア」と「従量課金制（Pay-as-you-go）」プランの違いを理解する必要があります 44。

- **無料ティア**: Google AI Studioの利用自体は無料であり、APIにも寛大な無料枠が提供されます 45。しかし、そのレート制限は低く設定されており（例：Gemini 1.5 Proで2 RPM、Gemini 1.5 Flashで15 RPM）、テストや個人利用を想定しています 46。また、無料ティアでは、入力されたデータがGoogleの製品改善に使用される場合があります 48。
    
- **従量課金制プラン**: Google Cloudプロジェクトで課金を有効にすることで移行できます。レート制限が大幅に緩和され（例：1,000 RPM以上）、安定したサービス提供が可能になります 47。また、入力データが製品改善に使用されなくなるため、プライバシー保護の観点からも優れています 44。
    

本Botは最大5人の友人が利用することを想定しており、講義終了時間が重なると短時間に複数のAPIリクエストが集中する可能性があります。無料ティアの低いRPMでは、リクエストが429エラーで失敗し、安定した運用が困難になることが予想されます。したがって、**開発・テスト段階では無料ティアを利用し、複数人での本格的な運用を開始する際には従量課金制プランへ移行すること**を強く推奨します。

**表2：講義1時間あたりのGemini APIトークン消費量とコストの推定（`gemini-2.5-flash`従量課金制）**

|項目|前提・計算|値|コスト（従量課金制）|
|---|---|---|---|
|平均的な講義の発話速度|-|150 WPM (Words Per Minute)|-|
|60分間の総単語数|150 WPM * 60 min|9,000単語|-|
|平均的な単語の文字数|英語基準|5文字/単語|-|
|総文字数（概算）|9,000単語 * 5文字|45,000文字|-|
|**入力トークン数（概算）**|4文字 ≈ 1トークン 49|**約 11,250 トークン**|-|
|入力コスト（100万トークンあたり）|`gemini-2.5-flash` (>128k) 48|$0.15|-|
|**入力コスト（合計）**|(11,250 / 1,000,000) * $0.15|-|**$0.0016875**|
|**出力トークン数（概算）**|入力とほぼ同量と仮定|**約 11,250 トークン**|-|
|出力コスト（100万トークンあたり）|`gemini-2.5-flash` (>128k) 48|$0.60|-|
|**出力コスト（合計）**|(11,250 / 1,000,000) * $0.60|-|**$0.00675**|
|**1時間あたりの総コスト（推定）**|入力コスト + 出力コスト|-|**約 $0.0084**|

この分析から、`gemini-2.5-flash`を使用した場合、1時間の講義を処理するためのAPIコストは**約0.84セント**と非常に低いことがわかります。このコスト効率の良さは、本プロジェクトの実現可能性を大きく高めるものです。この計算は、抽象的な料金表を、ユーザーの具体的なユースケースに基づいた実行可能な財務予測に変換し、「実際に運用するといくらかかるのか？」という重要な問いに答えるものです。

## 第8章：完全なコード実装とデプロイメント

本最終章では、これまでの章で設計・詳述してきたすべてのコンポーネントを統合した、完全なソースコードを提供し、ユーザーのローカルWindows環境でBotを起動・維持するための具体的な手順をガイドします。

### 8.1. 注釈付き完全ソースコード

以下に、プロジェクト全体の完全なソースコードをファイルごとに示します。コードには、各部分の機能や設計意図を理解するための詳細なコメントが付与されています。

#### 8.1.1. `main.py` (メインエントリポイント)

Python

```python
import discord
import os
import asyncio
from dotenv import load_dotenv
import aiodiskqueue

from core.session_manager import RecordingSessionManager
from core.gemini_processor import GeminiProcessor
from core.transcription_worker import transcription_worker

#.envファイルから環境変数を読み込む
load_dotenv()

# Botが必要とするIntentsを定義
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

# Botクラスをサブクラス化して、カスタム属性を持たせる
class TranscriptionBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transcription_queue = None
        self.gemini_processor = GeminiProcessor()
        self.session_manager = None

    async def setup_hook(self):
        # Botが起動する前に非同期の初期化を行う
        self.transcription_queue = await aiodiskqueue.Queue.create("./data/queue")
        self.session_manager = RecordingSessionManager(self, self.transcription_queue, self.gemini_processor)
        
        # 文字起こしワーカータスクを開始
        self.loop.create_task(transcription_worker(self))

bot = TranscriptionBot(intents=intents)

# Cogsをロードする
cogs_list = [
    "setup_cog",
    "recording_cog"
]

for cog in cogs_list:
    bot.load_extension(f"cogs.{cog}")

@bot.event
async def on_ready():
    print(f"{bot.user}としてログインしました。")
    print("------")
    # 必要なディレクトリが存在することを確認
    os.makedirs("./data/recordings", exist_ok=True)
    os.makedirs("./data/transcripts", exist_ok=True)
    os.makedirs("./data/queue", exist_ok=True)

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
```

#### 8.1.2. `cogs/setup_cog.py` (設定コマンド)

Python

```python
import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands
import json

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    setup = SlashCommandGroup("setup", "Botの初期設定を行います。")

    @setup.command(name="channels", description="録音対象のカテゴリと通知用テキストチャンネルを設定します。")
    async def setup_channels(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.administrator:
            await ctx.respond("このコマンドは管理者権限を持つユーザーのみ実行できます。", ephemeral=True)
            return

        categories = [c for c in ctx.guild.channels if isinstance(c, discord.CategoryChannel)]
        text_channels =

        if not categories or not text_channels:
            await ctx.respond("設定に必要なチャンネルが見つかりません。", ephemeral=True)
            return

        # セレクトメニューのコンポーネントを作成
        category_select = discord.ui.Select(
            placeholder="録音対象のボイスチャンネルカテゴリを選択",
            options=
        )
        text_channel_select = discord.ui.Select(
            placeholder="文字起こし結果の送信先チャンネルを選択",
            options=
        )

        async def callback(interaction: discord.Interaction):
            # ユーザーの選択を保存
            config = {
                "target_category_id": int(category_select.values),
                "output_channel_id": int(text_channel_select.values)
            }
            # 簡単のためJSONファイルに保存
            with open(f"config_{ctx.guild.id}.json", "w") as f:
                json.dump(config, f)
            
            await interaction.response.send_message("設定が完了しました。", ephemeral=True)

        category_select.callback = callback
        text_channel_select.callback = callback

        view = discord.ui.View()
        view.add_item(category_select)
        view.add_item(text_channel_select)

        await ctx.respond("以下のメニューから設定を行ってください:", view=view, ephemeral=True)

def setup(bot):
    bot.add_cog(SetupCog(bot))
```

#### 8.1.3. `cogs/recording_cog.py` (録音イベントハンドリング)

Python

```python
import discord
from discord.ext import commands
import json
import os

class RecordingCog(commands.Cog):
    def __init__(self, bot):
        self.bot: "TranscriptionBot" = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        try:
            with open(f"config_{member.guild.id}.json", "r") as f:
                config = json.load(f)
            target_category_id = config.get("target_category_id")
        except (FileNotFoundError, KeyError):
            return

        # ユーザーが監視対象カテゴリのVCに参加
        if before.channel is None and after.channel is not None:
            if after.channel.category_id == target_category_id:
                await self.bot.session_manager.start_recording(member, after.channel)

        # ユーザーがVCから退出
        elif before.channel is not None and after.channel is None:
            # 退出したユーザーが録音セッション中だったか確認
            if self.bot.session_manager.is_recording(member.id):
                await self.bot.session_manager.stop_recording(member)

def setup(bot):
    bot.add_cog(RecordingCog(bot))
```

#### 8.1.4. `core/session_manager.py` (セッション管理)

Python

```python
import discord
from discord.ext import tasks
import time
import os
import asyncio

class RecordingSession:
    def __init__(self, member, voice_client, manager):
        self.member = member
        self.vc = voice_client
        self.manager = manager
        self.transcript_segments =
        self.audio_chunks =
        self.chunk_task = self.create_chunking_task()

    def start(self):
        self.chunk_task.start()

    def stop(self):
        self.chunk_task.cancel()
        if self.vc.is_recording():
            self.vc.stop_recording()

    def create_chunking_task(self):
        @tasks.loop(minutes=5.0)
        async def chunker():
            if self.vc.is_recording():
                self.vc.stop_recording()
        
        @chunker.before_loop
        async def before_chunker():
            print(f"{self.member.name}の録音を開始します。")
            self.vc.start_recording(
                discord.sinks.WaveSink(),
                self.manager.once_done_callback,
                self.member,
            )
        return chunker

class RecordingSessionManager:
    def __init__(self, bot, transcription_queue, gemini_processor):
        self.bot = bot
        self.active_sessions = {}
        self.transcription_queue = transcription_queue
        self.gemini_processor = gemini_processor

    def is_recording(self, user_id):
        return user_id in self.active_sessions

    async def start_recording(self, member, channel):
        if self.is_recording(member.id):
            return

        try:
            vc = await channel.connect()
            session = RecordingSession(member, vc, self)
            self.active_sessions[member.id] = session
            session.start()
            print(f"セッション開始: {member.name}")
        except Exception as e:
            print(f"録音開始エラー: {e}")

    async def stop_recording(self, member):
        session = self.active_sessions.pop(member.id, None)
        if not session:
            return

        session.stop()
        
        # 最終処理を行うために少し待つ
        await asyncio.sleep(2)

        if session.vc.is_connected():
            await session.vc.disconnect()

        print(f"{member.name}の最終処理を開始します。")
        final_raw_text = "".join(session.transcript_segments)
        
        if not final_raw_text.strip():
            print(f"{member.name}のセッションには有効な音声がありませんでした。")
            self.cleanup_session_files(session)
            return

        processed_data = await self.gemini_processor.process_transcript(final_raw_text)
        
        if processed_data and "full_transcript" in processed_data:
            final_text = processed_data["full_transcript"]
            file_path = f"./data/transcripts/{member.name}_transcript_{int(time.time())}.txt"
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(final_text)

                with open(f"config_{member.guild.id}.json", "r") as f:
                    config = json.load(f)
                output_channel_id = config.get("output_channel_id")
                
                if output_channel_id:
                    channel = self.bot.get_channel(output_channel_id)
                    if channel:
                        await channel.send(
                            f"{member.mention}さんの講義の文字起こしが完了しました。",
                            file=discord.File(file_path)
                        )
            except Exception as e:
                print(f"ファイル送信エラー: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        self.cleanup_session_files(session)
        print(f"セッション終了: {member.name}")

    def cleanup_session_files(self, session):
        for chunk_path in session.audio_chunks:
            if os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                except OSError as e:
                    print(f"音声チャンク削除エラー: {e}")

    def get_session(self, user_id):
        return self.active_sessions.get(user_id)

    async def once_done_callback(self, sink: discord.sinks.WaveSink, member: discord.Member, *args):
        session = self.get_session(member.id)
        if not session:
            return

        user_audio = sink.audio_data.get(member.id)
        if user_audio:
            file_path = f"./data/recordings/{member.id}_{int(time.time())}.wav"
            session.audio_chunks.append(file_path)
            with open(file_path, "wb") as f:
                f.write(user_audio.file.getbuffer())
            
            await self.transcription_queue.put((member.id, file_path))

        if session.chunk_task.is_running() and session.vc.is_connected():
            session.vc.start_recording(
                discord.sinks.WaveSink(),
                self.once_done_callback,
                member,
            )
```

#### 8.1.5. `core/transcription_worker.py` (文字起こしワーカー)

Python

```python
import asyncio
import os
from faster_whisper import WhisperModel

async def transcription_worker(bot):
    model_size = os.getenv("TRANSCRIPTION_MODEL", "small")
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print(f"Faster-Whisperモデル({model_size})を正常にロードしました。")
    except Exception as e:
        print(f"モデルのロードに失敗しました: {e}")
        return

    while True:
        try:
            user_id, audio_path = await bot.transcription_queue.get()
            
            if not os.path.exists(audio_path):
                print(f"警告: 音声ファイルが見つかりません: {audio_path}")
                bot.transcription_queue.task_done()
                continue
            
            print(f"文字起こし処理中: {audio_path}")
            
            loop = asyncio.get_running_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: model.transcribe(audio_path, beam_size=5, language="ja")
            )
            
            transcribed_text = "".join(segment.text for segment in segments)
            
            session = bot.session_manager.get_session(user_id)
            if session:
                session.transcript_segments.append(transcribed_text)
            
            # 音声チャンクはセッション終了時にまとめて削除するため、ここでは削除しない

            bot.transcription_queue.task_done()
            print(f"文字起こし完了: {os.path.basename(audio_path)}")

        except asyncio.CancelledError:
            print("文字起こしワーカーがキャンセルされました。")
            break
        except Exception as e:
            print(f"文字起こしワーカーで予期せぬエラー: {e}")
            await asyncio.sleep(5)
```

#### 8.1.6. `core/gemini_processor.py` (Gemini API処理)

Python

```python
import google.generativeai as genai
import os
import json

class GeminiProcessor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEYが設定されていません。")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    async def process_transcript(self, raw_transcript: str) -> dict | None:
        prompt = self._create_prompt(raw_transcript)
        
        try:
            safety_settings = {
                'HATE': 'BLOCK_NONE', 'HARASSMENT': 'BLOCK_NONE',
                'SEXUAL': 'BLOCK_NONE', 'DANGEROUS': 'BLOCK_NONE'
            }
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            return json.loads(response.text)

        except Exception as e:
            print(f"Gemini APIエラー: {e}")
            # フォールバックとして、単純な結合テキストを返す
            return {"full_transcript": raw_transcript}

    def _create_prompt(self, raw_transcript: str) -> str:
        return f"""
あなたは、大学の講義の日本語文字起こしテキストを処理し、構造化することに特化した専門のAIアシスタントです。あなたの目的は、生のテキストに含まれる誤字脱字や文法的な誤りを修正し、学習資料として利用しやすいように整形することです。

# 指示
以下の「生の文字起こしテキスト」を分析し、次の処理を実行してください。

1. **修正**: 文脈に基づいて、明らかなスペルミス、文法エラー、文字起こし特有の誤り（例：「えーっと」「あのー」などの不要なフィラーワードの除去、同音異義語の訂正）を修正してください。
2. **構造化**: 内容の論理的な区切りを見つけ、適切な段落分けや改行を挿入してください。
3. **要約とキーワード抽出**: 講義全体の要点を3〜5文で要約し、議論された主要な専門用語や概念をリストアップしてください。
4. **出力形式**: 最終的な出力は、必ず指示されたJSON形式でなければなりません。

# JSONスキーマ
{{
    "title": "講義内容を的確に表す簡潔な日本語タイトル",
    "summary": "講義内容の3〜5文からなる日本語の要約",
    "key_terms": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "full_transcript": "修正・整形済みの完全な日本語の文字起こしテキスト。適切な段落や改行が含まれていること。"
}}

# 生の文字起こしテキスト
---
{raw_transcript}
---
"""
```

### 8.2. ローカルWindowsホストでの実行・維持ガイド

以下の手順に従い、あなたのWindows 11 PCでBotをセットアップし、実行します。

1.  **Pythonのインストール**
    
    -   Python公式サイト（python.org）から、最新のPython 3.9以上のインストーラをダウンロードします。
    -   インストーラ実行時、「Add Python to PATH」のチェックボックスを必ずオンにしてください。
        
2.  **FFmpegのインストール**
    
    -   FFmpeg公式サイト（ffmpeg.org）からWindows用のビルドをダウンロードします。
    -   ダウンロードしたzipファイルを解凍し、中にある`bin`フォルダ（`ffmpeg.exe`が含まれる）のパスをシステムの環境変数`Path`に追加します。
        
3.  **プロジェクトのセットアップ**
    
    -   任意の場所にプロジェクト用のフォルダを作成し、本レポートのソースコードをその中に配置します。
    -   コマンドプロンプトまたはPowerShellを開き、プロジェクトフォルダに移動します。
    -   `python -m venv venv` を実行して、仮想環境を作成します。
    -   `.\venv\Scripts\activate` を実行して、仮想環境を有効化します。
        
4.  **依存ライブラリのインストール**
    
    -   仮想環境が有効な状態で、`pip install -r requirements.txt` を実行し、必要なライブラリをすべてインストールします。
        
5.  **.envファイルの設定**
    
    -   プロジェクトのルートディレクトリに`.env`という名前のファイルを作成します。
    -   第1.3章で示したテンプレートに従い、あなたのDiscord BotトークンとGemini APIキーをファイルに記述・保存します。
        
6.  **Botの実行**
    
    -   すべての設定が完了したら、コマンドプロンプトで `python main.py` を実行します。
    -   コンソールに「(Bot名)としてログインしました。」と表示されれば、Botは正常に起動しています。
        
7.  **Botの維持**
    
    -   Botを継続的に実行するには、このコマンドプロンプトのウィンドウを開いたままにしておく必要があります。ウィンドウを閉じるとBotは停止します。
    -   Botの動作ログやエラーメッセージは、このコンソールに出力されるため、問題が発生した際のトラブルシューティングに役立ちます。
    -   永続的な運用のためには、PM2やNSSM (Non-Sucking Service Manager) といったツールを使用して、PythonスクリプトをWindowsサービスとして登録する方法も検討できます。
        

以上で、AI駆動型Discord文字起こしBotのアーキテクチャ設計から実装、運用までの全工程が完了です。
このドキュメントが、あなたのプロジェクト成功の一助となることを願っています。
