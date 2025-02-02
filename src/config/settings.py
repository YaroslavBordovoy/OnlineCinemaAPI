import base64
import os
from pathlib import Path
from dotenv import load_dotenv

from pydantic_settings import BaseSettings


load_dotenv()

RANDOM_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(BASE_DIR / "database" / "cinema.db")


class Settings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", RANDOM_KEY)
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", RANDOM_KEY)
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")


class TestingSettings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = "SECRET_KEY_ACCESS"
    SECRET_KEY_REFRESH: str = "SECRET_KEY_REFRESH"
    JWT_SIGNING_ALGORITHM: str = "HS256"
