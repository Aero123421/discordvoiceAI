import os
import json
import google.generativeai as genai


class GeminiProcessor:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        )

    async def process_transcript(self, raw: str) -> dict | None:
        prompt = self._create_prompt(raw)
        try:
            safety_settings = {
                k: "BLOCK_NONE"
                for k in ["HATE", "HARASSMENT", "SEXUAL", "DANGEROUS"]
            }
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
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
