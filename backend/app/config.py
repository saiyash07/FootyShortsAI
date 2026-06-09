import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = "sqlite:///./automation.db"
    GEMINI_API_KEY: str = ""
    GOOGLE_DRIVE_FOLDER_ID: str = "1I8FGWyUsJkQ3CqOdYv7XXNAIJsQezuvU"
    GOOGLE_DRIVE_UPLOADED_FOLDER_ID: str = ""
    GOOGLE_CLIENT_SECRETS_FILE: str = "credentials.json"
    GOOGLE_TOKEN_FILE: str = "token.json"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
