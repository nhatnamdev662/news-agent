from .custom import CustomProvider
from .base import BaseLLMProvider


def get_provider(provider_name: str = "custom"):
    return CustomProvider()


def list_providers() -> list:
    return ["custom"]
