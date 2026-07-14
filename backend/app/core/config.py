from functools import lru_cache
from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str
    password: SecretStr
    database: str = "quant_platform"

    @field_validator("user")
    @classmethod
    def user_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("database user is required")
        return v.strip()

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
    latest_price_cache_ttl_seconds: int = 604800
    
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class JWTSettings(BaseModel):
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 30

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_empty(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("JWT secret_key is required and must not be empty")
        return v


class EncryptSettings(BaseModel):
    credentials_key: SecretStr # broker_accounts.credentials_encrypted 用的 Fernet key

    @field_validator("credentials_key")
    @classmethod
    def key_must_not_be_empty(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("credentials_key is required and must not be empty")
        return v


class LLMSettings(BaseModel):
    provider: str = "openai"
    api_key: SecretStr = SecretStr("")
    model: str = "gpt-3.5-turbo"
    rate_limit_per_minute: int = 10
    max_agent_rounds: int = 5
    message_max_length: int = 4096


class TradingSettings(BaseModel):
    enabled_default: bool = True
    default_backtest_capital: int = 1_000_000


class BacktestWorkerSettings(BaseModel):
    """回测 worker 子进程资源限制与超时配置"""
    max_memory_mb: int = 512              # 子进程最大内存 (MB)
    max_cpu_seconds: int = 300            # 子进程最大 CPU 时间 (秒)，对应 SIGALRM
    worker_timeout_seconds: int = 305     # worker 内部超时信号（比 cpu 超时多 5s 缓冲）
    process_join_timeout: int = 320       # 主进程等待子进程退出超时（比 worker 超时多 15s）


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
    llm: LLMSettings
    trading: TradingSettings = TradingSettings()
    backtest_worker: BacktestWorkerSettings = BacktestWorkerSettings()

    cors_origins: list[str] = ["http://localhost:3000"]
    kline_fetch_interval_seconds: int = 3
    default_page_size: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
