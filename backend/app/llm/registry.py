from sqlmodel import Session, select

from app.config import LLM_TIMEOUT, OLLAMA_URL
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import Provider, ProviderError
from app.llm.ollama import OllamaProvider
from app.models import ProviderConfig

# Anthropic needs no URL; its key comes from the environment.
DEFAULT_BASE_URLS: dict[str, str | None] = {"ollama": OLLAMA_URL, "anthropic": None}


def build_provider(config: ProviderConfig) -> Provider:
    if config.provider == "ollama":
        return OllamaProvider(config.base_url or OLLAMA_URL, config.model, LLM_TIMEOUT)
    if config.provider == "anthropic":
        return AnthropicProvider(config.model, LLM_TIMEOUT)
    raise ProviderError(f"Unsupported provider {config.provider!r}")


class NoProviderEnabled(ProviderError):
    pass


def get_active_provider(session: Session) -> tuple[ProviderConfig, Provider]:
    config = session.exec(select(ProviderConfig).where(ProviderConfig.enabled)).first()
    if config is None:
        raise NoProviderEnabled("No LLM provider is enabled. Add one under Settings.")
    return config, build_provider(config)
