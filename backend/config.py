from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "health-risk-backend"
    ENV: str = "dev"
    DEBUG: bool = True

    ML_HOST: str = "0.0.0.0"
    ML_BASE_URL: str = f"http://{ML_HOST}:8001"
    ML_PREDICT_PATH: str = "/predict"
    ML_TIMEOUT_SECONDS: int = 5

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "healthrisk"
    DB_USER: str = "postgres"
    DB_PASS: str = "1234"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
