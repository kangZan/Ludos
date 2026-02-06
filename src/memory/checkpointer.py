"""Checkpointer factory — InMemorySaver for dev, AsyncPostgresSaver for production."""

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from src.config.settings import settings

logger = structlog.get_logger(__name__)


async def get_checkpointer() -> BaseCheckpointSaver:
    """Create and return the appropriate checkpointer based on environment.

    - Development: InMemorySaver (no external dependencies)
    - Production: AsyncPostgresSaver (requires PostgreSQL)

    Returns:
        Configured checkpointer instance.
    """
    if settings.is_production and settings.db_url:
        return await _create_postgres_checkpointer()

    logger.info("checkpointer.using_memory", env=settings.env)
    return InMemorySaver()


async def _create_postgres_checkpointer() -> BaseCheckpointSaver:
    """Create a PostgreSQL-backed checkpointer for production use."""
    try:
        from langgraph_checkpoint_postgres import AsyncPostgresSaver

        checkpointer = AsyncPostgresSaver(conn_string=settings.db_url)
        await checkpointer.setup()

        logger.info("checkpointer.using_postgres", db_url=settings.db_url[:30] + "...")
        return checkpointer

    except ImportError:
        logger.warning(
            "checkpointer.postgres_unavailable",
            detail="langgraph-checkpoint-postgres not installed, falling back to InMemorySaver",
        )
        return InMemorySaver()

    except Exception:
        logger.exception("checkpointer.postgres_setup_failed")
        logger.warning("checkpointer.fallback_to_memory")
        return InMemorySaver()
