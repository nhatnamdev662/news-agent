import os
import requests
import asyncio
from .base import BaseLLMProvider

class DarkAPIProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("DARKAPI_KEY")
        self.model = os.getenv("DARKAPI_MODEL", "laguna-s-2.1-free")
        self.base_url = "https://api.darkapi.dev/v1"
    
    async def chat(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        def _request():
            return requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            )
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _request)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            raise Exception(f"DarkAPI error: {str(e)}")
