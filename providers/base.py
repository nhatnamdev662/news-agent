import os
from abc import ABC, abstractmethod
from typing import Optional

class BaseLLMProvider(ABC):
    """Abstract class cho các provider LLM"""
    
    def __init__(self):
        self.api_key = None
        self.model = None
        self.base_url = None
    
    @abstractmethod
    async def chat(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Gửi prompt và nhận phản hồi"""
        pass
    
    async def summarize(self, text: str) -> str:
        """Tóm tắt văn bản"""
        prompt = f"""
Bạn là chuyên gia rút gọn tin tức. Hãy tóm tắt đoạn văn bản sau thành 2-3 câu ngắn gọn, giữ lại thông tin quan trọng nhất:

Văn bản:
{text}

Tóm tắt:
"""
        return await self.chat(prompt, max_tokens=512, temperature=0.3)
    
    async def classify(self, title: str, content: str = "") -> str:
        """Phân loại tin tức"""
        prompt = f"""
Phân loại tin tức sau vào một trong các thể loại: Thể thao, Công nghệ, Kinh tế, Chính trị, Xã hội, Giải trí, Du lịch, Ẩm thực

Tiêu đề: {title}
Nội dung: {content[:200] if content else "Không có nội dung"}

Thể loại:
"""
        return await self.chat(prompt, max_tokens=50, temperature=0.1)
