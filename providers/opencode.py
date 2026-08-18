import os
import asyncio
from .base import BaseLLMProvider

DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_MODEL = "deepseek-v4-flash-free"


class OpenCodeProvider(BaseLLMProvider):
    """Provider OpenCode — không cần API key, miễn phí."""

    def __init__(self):
        super().__init__()
        url = os.getenv("OPENCODE_API_URL", "").strip()
        self.base_url = url if url else DEFAULT_BASE_URL
        model = os.getenv("OPENCODE_MODEL", "").strip()
        self.model = model if model else DEFAULT_MODEL
        self.timeout = 30

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def fetch_models(self) -> list:
        import requests
        try:
            resp = requests.get(
                self.base_url + "/models",
                headers=self._headers(),
                timeout=10
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return sorted([m["id"] for m in data.get("data", []) if m.get("id")])
        except Exception:
            return []

    def _payload(self, prompt, max_tokens, temperature):
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    async def chat(self, prompt, max_tokens=2048, temperature=0.7):
        import requests
        headers = self._headers()
        payload = self._payload(prompt, max_tokens, temperature)

        def _post():
            return requests.post(
                self.base_url + "/chat/completions",
                json=payload, headers=headers, timeout=self.timeout
            )

        try:
            resp = await asyncio.get_event_loop().run_in_executor(None, _post)
        except Exception as exc:
            raise RuntimeError("Kết nối OpenCode thất bại: " + str(exc))

        body = resp.text.strip()
        if resp.status_code != 200:
            raise RuntimeError("OpenCode HTTP " + str(resp.status_code) + " | " + body[:200])
        if not body:
            raise RuntimeError("OpenCode trả về rỗng")
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError("OpenCode JSON lỗi: " + body[:200])
        err = data.get("error")
        if err:
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise RuntimeError("OpenCode lỗi: " + str(msg))
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError("OpenCode không có 'choices': " + body[:200])
