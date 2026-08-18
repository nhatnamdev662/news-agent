import os
import asyncio
from .base import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    """Provider OpenAI-compatible (vd DarkAPI). Chế độ chuẩn, lỗi rõ nghĩa."""
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("CUSTOM_API_KEY", "").strip()
        self.model = os.getenv("CUSTOM_MODEL", "laguna-s-2.1-free").strip()
        self.base_url = os.getenv("CUSTOM_API_URL", "").strip().rstrip("/")
        self.timeout = 30

    def _payload(self, prompt, max_tokens, temperature):
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    async def chat(self, prompt, max_tokens=2048, temperature=0.7):
        if not (self.api_key and self.base_url):
            raise RuntimeError("CUSTOM_API_KEY hoặc CUSTOM_API_URL chưa cấu hình trong .env")
        import requests
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = self._payload(prompt, max_tokens, temperature)

        def _post():
            return requests.post(self.base_url + "/chat/completions",
                                 json=payload, headers=headers, timeout=self.timeout)

        try:
            resp = await asyncio.get_event_loop().run_in_executor(None, _post)
        except Exception as exc:
            raise RuntimeError("Ket noi provider that bai: " + str(exc))

        body = resp.text.strip()
        if resp.status_code != 200:
            raise RuntimeError("Provider tra ve HTTP " + str(resp.status_code) + " | body: " + body[:200])
        if not body:
            raise RuntimeError("Provider tra ve noi dung rong (empty body). Kiem tra API key / model / URL.")
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError("Provider tra ve JSON loi. body: " + body[:200])
        err = data.get("error")
        if err:
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise RuntimeError("Provider bao loi: " + str(msg))
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError("Provider khong tra ve 'choices'. body: " + body[:200])
