import os
import asyncio
from .base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    async def chat(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            raise ImportError("Vui lòng cài: pip install openai")
        except Exception as e:
            raise Exception(f"OpenAI error: {str(e)}")
