import os
import json
from google import genai


class GeminiProcessor:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def process_transcript(self, raw: str) -> dict | None:
        prompt = self._create_prompt(raw)
        try:
            safety_settings = [
                genai.types.SafetySetting(
                    category=genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=genai.types.HarmBlockThreshold.BLOCK_NONE,
                ),
                genai.types.SafetySetting(
                    category=genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=genai.types.HarmBlockThreshold.BLOCK_NONE,
                ),
                genai.types.SafetySetting(
                    category=genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=genai.types.HarmBlockThreshold.BLOCK_NONE,
                ),
                genai.types.SafetySetting(
                    category=genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=genai.types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
            config = genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=safety_settings,
            )
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini APIエラー: {e}")
            return {"full_transcript": raw}

    def _create_prompt(self, raw: str) -> str:
        return f"""
あなたは、大学の講義の日本語文字起こしテキストを処理し、構造化することに特化した専門のAIアシスタントです。あなたの目的は、生のテキストに含まれる誤字脱字や文法的な誤りを修正し、学習資料として利用しやすいように整形することです。

# 指示
以下の「生の文字起こしテキスト」を分析し、次の処理を実行してください。
1. **修正**: 文脈に基づいて、明らかなスペルミス、文法エラー、文字起こし特有の誤りを修正してください。
2. **構造化**: 内容の論理的な区切りを見つけ、適切な段落分けや改行を挿入してください。
3. **要約とキーワード抽出**: 講義全体の要点を3〜5文で要約し、主要な専門用語や概念をリストアップしてください。
4. **出力形式**: 最終的な出力は、必ず指示されたJSON形式でなければなりません。

# JSONスキーマ
{{
    "title": "講義内容を的確に表す簡潔な日本語タイトル",
    "summary": "講義内容の3〜5文からなる日本語の要約",
    "key_terms": ["キーワード1", "キーワード2", "キーワード3"],
    "full_transcript": "修正・整形済みの完全な日本語の文字起こしテキスト"
}}

# 生の文字起こしテキスト
---
{raw}
---

# 出力 (JSON形式)
"""
