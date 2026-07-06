import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str


def get_deepseek_config() -> DeepSeekConfig:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise ConfigError("python-dotenv is not installed. Please run: pip install -r requirements.txt") from exc

    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ConfigError("DEEPSEEK_API_KEY is missing. Please set it in .env before running the program.")

    return DeepSeekConfig(
        api_key=api_key,
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    )
