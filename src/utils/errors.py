"""Centralized error types and handling helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LudosError(Exception):
    """Base error for the Ludos application."""

    message: str
    details: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class ConfigurationError(LudosError):
    """Configuration-related errors."""


class DependencyError(LudosError):
    """Missing or incompatible dependencies."""


class RuntimeWorkflowError(LudosError):
    """Errors that occur during the graph execution."""
