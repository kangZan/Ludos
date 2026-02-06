"""Load the conversion prompt template from the doc directory."""

from pathlib import Path

_CONVERSION_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "doc"
    / "【叙事文本→角色驱动推演剧本】标准化转换提示词.md"
)

_cached_prompt: str | None = None


def load_conversion_prompt() -> str:
    """Load and cache the narrative-to-script conversion prompt template."""
    global _cached_prompt
    if _cached_prompt is not None:
        return _cached_prompt

    if not _CONVERSION_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Conversion prompt not found: {_CONVERSION_PROMPT_PATH}"
        )

    _cached_prompt = _CONVERSION_PROMPT_PATH.read_text(encoding="utf-8")
    return _cached_prompt
