"""Tool registry for dynamic tool discovery and plugin loading."""

from __future__ import annotations

import importlib
from typing import Callable

import structlog

from src.config.settings import settings
from src.utils.errors import ConfigurationError

logger = structlog.get_logger(__name__)

ToolFn = Callable[..., object]

_REGISTRY: dict[str, ToolFn] = {}


def register_tool(name: str, func: ToolFn) -> None:
    """Register a tool function by name."""
    if not name:
        raise ConfigurationError("Tool name cannot be empty")
    _REGISTRY[name] = func
    logger.info("tool.registered", name=name)


def get_tool(name: str) -> ToolFn | None:
    """Retrieve a tool by name."""
    return _REGISTRY.get(name)


def list_tools() -> list[str]:
    """List all registered tools."""
    return sorted(_REGISTRY.keys())


def load_tool_plugins() -> None:
    """Load tool plugins from settings.tool_plugins.

    Format: comma-separated module paths, e.g.:
      TOOL_PLUGINS=plugins.tools.extra,plugins.tools.more
    """
    raw = settings.tool_plugins.strip()
    if not raw:
        return

    for module_path in [p.strip() for p in raw.split(",") if p.strip()]:
        try:
            importlib.import_module(module_path)
            logger.info("tool.plugin_loaded", module=module_path)
        except Exception as exc:  # pragma: no cover - import time side effects
            logger.error("tool.plugin_failed", module=module_path, error=str(exc))
