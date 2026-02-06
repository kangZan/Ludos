"""Polishing agent — transforms raw interaction logs into literary narrative text."""

import structlog

from src.agents.llm_client import call_llm
from src.config.prompts import POLISHER_NARRATIVE
from pathlib import Path

logger = structlog.get_logger(__name__)


async def polish_narrative(
    raw_log: str,
    memory_dir: str,
    scene_info: str,
) -> str:
    """Transform raw interaction logs into vivid literary narrative prose.

    The polisher has access to ALL characters' inner states (including
    private information) to write accurate internal monologue and
    atmosphere. It never uses numerical values for conflict resolution.

    Args:
        raw_log: The raw interaction log text.
        character_dossiers: All character dossiers (with private info).
        scene_info: Scene description for atmosphere context.

    Returns:
        Polished narrative text.
    """
    # Format dossiers for the polisher from memory files
    dossiers_text_parts: list[str] = []
    memory_path = Path(memory_dir)
    if memory_path.exists():
        for mem_file in sorted(memory_path.glob("*.mem.txt")):
            char_id = mem_file.stem.replace(".mem", "")
            content = mem_file.read_text(encoding="utf-8")
            dossiers_text_parts.append(f"【{char_id}】\n{content}")

    dossiers_text = "\n".join(dossiers_text_parts)

    prompt = POLISHER_NARRATIVE.format(
        raw_log=raw_log,
        character_dossiers=dossiers_text,
        scene_info=scene_info,
    )

    logger.info(
        "polisher.polishing",
        raw_log_length=len(raw_log),
        num_characters=len(dossiers_text_parts),
    )

    result = await call_llm(
        system_prompt="你是一位文学叙事大师。请将原始交互日志转化为生动的叙事散文。直接输出叙事文本。",
        user_message=prompt,
        temperature=0.8,  # Slightly more creative for literary output
    )

    polished = result.get("content", "")

    logger.info("polisher.done", output_length=len(polished))
    return polished
