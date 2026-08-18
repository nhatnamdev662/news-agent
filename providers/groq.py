import os
import asyncio
from .base import BaseLLMProvider

class GroqProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    
    async def chat(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            raise ImportError("Vui lòng cài: pip install groq")
        except Exception as e:
            raise Exception(f"Groq error: {str(e)}")
