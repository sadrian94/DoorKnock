import json
import httpx
from typing import Dict, Any, Optional
from ..config import GEMINI_API_KEY, GEMINI_MODEL

class GeminiError(Exception):
    pass

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_configured():
            raise GeminiError("GEMINI_API_KEY is not configured. Please add GEMINI_API_KEY to DoorKnock/.env")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        contents = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Context / Instruction:\n{system_instruction}\n\nTask:\n{prompt}"}]
            })
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": prompt}]
            })

        payload = {
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.RequestError as e:
                raise GeminiError(f"Network error connecting to Gemini API: {str(e)}")

            if response.status_code != 200:
                err_text = response.text
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message", err_text)
                except Exception:
                    err_msg = err_text
                raise GeminiError(f"Gemini API error ({response.status_code}): {err_msg}")

            try:
                data = response.json()
                candidate_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(candidate_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                raise GeminiError(f"Failed to parse structured JSON from Gemini response: {str(e)}")
