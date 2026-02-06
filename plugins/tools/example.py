"""Example tool plugin for Ludos."""

from src.tools.registry import register_tool


def echo_upper(text: str) -> str:
    """Return the input text in uppercase."""
    return text.upper()


register_tool("echo_upper", echo_upper)
