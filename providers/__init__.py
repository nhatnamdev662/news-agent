from .custom import CustomProvider
from .opencode import OpenCodeProvider
from .base import BaseLLMProvider


def get_provider(provider_name: str = "custom"):
    providers = {
        "opencode": OpenCodeProvider,
        "custom": CustomProvider,
    }
    cls = providers.get(provider_name, CustomProvider)
    return cls()


def list_providers() -> list:
    return ["opencode", "custom"]
