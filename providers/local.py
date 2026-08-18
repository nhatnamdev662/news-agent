import os
from .base import BaseLLMProvider

class LocalProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        self.model_path = os.getenv("LOCAL_MODEL_PATH", "./models/model.gguf")
        self.llm = None
    
    def _load_model(self):
        if not self.llm:
            try:
                from llama_cpp import Llama
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_threads=2,
                    n_gpu_layers=0
                )
            except ImportError:
                raise ImportError("Vui lòng cài: pip install llama-cpp-python")
            except Exception as e:
                raise Exception(f"Lỗi tải model: {str(e)}")
        return self.llm
    
    async def chat(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        llm = self._load_model()
        try:
            output = llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["</s>", "[/INST]"]
            )
            return output['choices'][0]['text'].strip()
        except Exception as e:
            raise Exception(f"Local LLM error: {str(e)}")
