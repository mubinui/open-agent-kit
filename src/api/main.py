"""Main FastAPI application entry point."""

from src.api.app_factory import create_app

app = create_app()
