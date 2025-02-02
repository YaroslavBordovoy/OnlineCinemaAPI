import os
from dotenv import load_dotenv
from fastapi import Depends

from config.settings import TestingSettings, Settings, BaseAppSettings
from security.jwt_interface import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager


load_dotenv()

def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    secret_key_access = os.getenv("SECRET_KEY_ACCESS")
    secret_key_refresh = os.getenv("SECRET_KEY_REFRESH")
    print(f"ENV SECRET_KEY_ACCESS: {secret_key_access}")
    print(f"ENV SECRET_KEY_REFRESH: {secret_key_refresh}")
    return Settings()


def get_jwt_auth_manager(settings: BaseAppSettings = Depends(get_settings)) -> JWTAuthManagerInterface:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )
