from pathlib import Path

from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(BASE_DIR / "database" / "cinema.db")


class Settings(BaseAppSettings): ...


class TestingSettings(BaseAppSettings): ...
