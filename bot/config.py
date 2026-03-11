from dataclasses import dataclass
import os
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_url: str
    min_bet: int
    max_bet: int
    webhook_url: str | None
    webhook_path: str
    host: str
    port: int


class ConfigError(ValueError):
    """Raised when required config is missing or invalid."""


def _to_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be an integer, got: {raw!r}") from error

    if value <= 0:
        raise ConfigError(f"{name} must be > 0, got: {value}")
    return value


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ConfigError("BOT_TOKEN is required")

    min_bet = _to_int("MIN_BET", 10)
    max_bet = _to_int("MAX_BET", 1000)
    if min_bet > max_bet:
        raise ConfigError("MIN_BET cannot be greater than MAX_BET")

    return Settings(
        bot_token=bot_token,
        db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///./bot.db"),
        min_bet=min_bet,
        max_bet=max_bet,
        webhook_url=os.getenv("WEBHOOK_URL") or None,
        webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=_to_int("PORT", 8080),
    )
