from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://monitor:local-change-me@localhost:5432/monitor'
    admin_token: str = ''
    nlp_enabled: bool = False
    model_path: str = '/models/e5'
    model_version: str = 'uninstalled'
    sentiment_path: str = '/models/sentiment'
    sentiment_version: str = 'uninstalled'
    collect_interval: int = 900
    retention_days: int = 90
    collection_enabled: bool = True


settings = Settings()
