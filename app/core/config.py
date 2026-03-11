from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    database_url: str = 'postgresql+psycopg://postgres:postgres@localhost:5432/tg_bot'
    spin_rate_limit_per_minute: int = 20


settings = Settings()
