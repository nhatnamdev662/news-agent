from .custom import CustomProvider
from .base import BaseLLMProvider

def get_provider(provider_name: str = "custom"):
    providers = {
        "custom": CustomProvider(),
    }
    return providers.get(provider_name, CustomProvider())
