"""FastAPI application lifecycle management."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI

from src.config.config_loader import get_config_loader
from src.config.llm_provider import get_provider_config
from src.config.settings import get_settings
from src.observability.tracing import configure_tracing, instrument_fastapi

logger = structlog.get_logger(__name__)


def _run_database_migrations() -> None:
    """Apply Alembic migrations so a fresh install works with zero setup.

    Skippable via OAK_AUTO_MIGRATE=false (e.g. when migrations are managed
    externally in production).
    """
    if os.environ.get("OAK_AUTO_MIGRATE", "true").lower() in ("0", "false", "no"):
        logger.info("database_auto_migration_skipped")
        return

    try:
        from alembic import command
        from alembic.config import Config

        project_root = Path(__file__).resolve().parents[2]
        alembic_cfg = Config(str(project_root / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))

        # Alembic needs a sync driver URL
        settings = get_settings()
        url = settings.database_url
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        url = url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        alembic_cfg.set_main_option("sqlalchemy.url", url)

        command.upgrade(alembic_cfg, "head")
        logger.info("database_migrations_applied", database=url.split("@")[-1])
    except Exception as exc:
        logger.error("database_migration_failed", error=str(exc), exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and clean up application-wide services."""
    settings = get_settings()
    logger.info(
        "open_agent_kit_starting",
        log_level=settings.app.log_level,
        environment=settings.app.environment,
    )

    # Ensure the data directory exists (SQLite DB, sessions, deployments)
    Path("./data").mkdir(parents=True, exist_ok=True)

    _run_database_migrations()

    try:
        from src.api.auth import bootstrap_admin_user

        bootstrap_admin_user()
    except Exception as exc:
        logger.warning("admin_bootstrap_failed", error=str(exc))

    try:
        provider_config = get_provider_config()
        logger.info(
            "llm_provider_configured",
            provider=provider_config.provider.value,
            model=provider_config.model_name,
            fallback_provider=(
                provider_config.fallback_provider.value
                if provider_config.fallback_provider
                else None
            ),
            cache_enabled=provider_config.enable_cache,
        )
        logger.info("llm_provider_ready", note="connection_test_skipped_for_fast_startup")
    except Exception as exc:
        logger.error("llm_provider_initialization_failed", error=str(exc), exc_info=True)

    enable_hot_reload = settings.app.environment == "development"
    try:
        config_loader = get_config_loader(enable_hot_reload=enable_hot_reload)
        logger.info(
            "config_loader_initialized",
            hot_reload=enable_hot_reload,
            config_dir=str(config_loader.config_dir),
        )
    except Exception as exc:
        logger.error("config_loader_initialization_failed", error=str(exc))

    try:
        configure_tracing()
        instrument_fastapi(app)
    except Exception as exc:
        logger.warning("tracing_configuration_failed", error=str(exc))

    yield

    logger.info("open_agent_kit_shutting_down")
    try:
        config_loader = get_config_loader()
        config_loader.stop_file_watcher()
    except Exception as exc:
        logger.warning("config_loader_cleanup_failed", error=str(exc))