from functools import lru_cache
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str
    password: SecretStr
    database: str = "quant_platform"

    @property
    def url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:"
            f"{self.password.get_secret_value()}@{self.host}:{self.port}/{self.database}"
        )


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class JWTSettings(BaseModel):
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 30


class EncryptSettings(BaseModel):
    credentials_key: SecretStr # broker_accounts.credentials_encrypted 用的 Fernet key


class LLMSettings(BaseModel):
    provider: str = "openai"
    api_key: SecretStr
    model: str = "gpt-3.5-turbo"
    rate_limit_per_minute: int = 10


class TradingSettings(BaseModel):
    enabled_default: bool = True


class Settings(BaseSettings):
    """
    Pydantic v2 固定命名 model_config 不可更改，
    创建Settings()实例时，自动读取model_config
    """
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        env_nested_delimiter = "__", # DB__PASSWORD 会自动映射进 DatabaseSettings.password
        extra = "ignore",
    )

    app_name: str = "quant-platform-api"
    env: str = "dev" # dev, test, prod
    debug: bool = True

    db: DatabaseSettings
    redis: RedisSettings = RedisSettings()
    jwt: JWTSettings
    encrypt: EncryptSettings
    llm: LLMSettings = LLMSettings()
    trading: TradingSettings = TradingSettings()

    cors_origins: list[str] = ["http://localhost:3000"]
    kline_fetch_interval_seconds: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()

    