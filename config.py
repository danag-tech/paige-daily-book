import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str


@dataclass(frozen=True)
class EmailConfig:
    email_user: str
    email_password: str
    email_to: str


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise ConfigError("python-dotenv is not installed. Please run: pip install -r requirements.txt") from exc

    load_dotenv()


def get_deepseek_config() -> DeepSeekConfig:
    _load_env()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ConfigError("DEEPSEEK_API_KEY is missing. Please set it in .env before running the program.")

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if not model:
        raise ConfigError("DEEPSEEK_MODEL is missing. Please set it in .env before running the program.")

    return DeepSeekConfig(
        api_key=api_key,
        model=model,
    )


def get_email_config() -> EmailConfig:
    _load_env()

    email_user = os.getenv("EMAIL_USER")
    if not email_user:
        raise ConfigError("EMAIL_USER is missing. Please set it in .env before sending email.")

    email_password = os.getenv("EMAIL_PASSWORD")
    if not email_password:
        raise ConfigError("EMAIL_PASSWORD is missing. Please set it in .env before sending email.")

    email_to = os.getenv("EMAIL_TO")
    if not email_to:
        raise ConfigError("EMAIL_TO is missing. Please set it in .env before sending email.")

    return EmailConfig(
        email_user=email_user,
        email_password=email_password,
        email_to=email_to,
    )
