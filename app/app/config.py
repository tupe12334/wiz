import os


class Config:
    """Application configuration."""

    DATABASE_CONNECTION_STRING = os.environ.get("DATABASE_CONNECTION_STRING")
    CREDENTIAL_STORE_API = os.environ.get("CREDENTIAL_STORE_API")
    SESSION_DURATION_HOURS = 24
