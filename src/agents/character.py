"""Character agent — autonomous decision-making from a single character's perspective."""

import structlog

from src.agents.llm_client import call_llm
from src.config.prompts import CHARACTER_DECISION
from src.models.types import ActionPack
from src.tools.info_filter import filter_visible_actions
from src.tools.pressure_tracker import DECAY_PER_ROUND, KEYWORD_MATCH_DELTA
from src.tools.text_formatter import (
    format_pressure_warning,
    format_visible_actions,
)
from src.utils.character_memory import load_memory, save_memory, seed_memory_if_missing
from src.utils.memory_protocol import parse_memory_update

logger = structlog.get_logger(__name__)


async def decide_action(
    character_id: str,
    scene_description: str,
    all_round_actions: list[ActionPack],
    last_inner_thoughts: str,
    current_round: int,
    current_turn: int,
    retry_feedback: str = "",
    public_log_path: str | None = None,
    memory_dir: str = "data/characters",
    goals: list[dict] | None = None,
) -> ActionPack:
    """Have a character make an autonomous decision based on their dossier.

    This is the core of character-driven narrative: the character acts
    based only on what they know, guided by their goals and personality.

    Args:
        scene_description: Current scene state (objective).
        all_round_actions: All actions this round (will be filtered).
        last_inner_thoughts: Character's inner thoughts from last round.
        current_round: Current round number.
        current_turn: Current turn within the round.
        retry_feedback: Feedback from validation (if retrying).

    Returns:
        The character's ActionPack.
    """
    char_id = character_id

    # Layer 1: Structural filtering — only show what this character can see
    visible = filter_visible_actions(all_round_actions, char_id)

    # Prepare memory file
    memory_path = f"{memory_dir}/{char_id}.mem.txt"
    seed_memory_if_missing(memory_path, f"身份：{char_id}", goals=[], secrets=[])

    memory = load_memory(memory_path)

    # Read new public broadcast (delta)
    public_delta = ""
    if public_log_path:
        try:
            with open(public_log_path, "r", encoding="utf-8") as f:
                f.seek(memory.last_public_offset)
                public_delta = f.read()
                memory.last_public_offset = f.tell()
        except FileNotFoundError:
            public_delta = ""

    # Format all sections for the prompt
    visible_text = format_visible_actions(visible)
    # Update secret pressures based on public delta
    triggered = False
    if public_delta:
        for secret in memory.secrets:
            if secret.get("is_revealed"):
                continue
            secret_id = secret.get("secret_id", "")
            keywords = secret.get("keywords", [])
            for keyword in keywords:
                if keyword and keyword in public_delta:
                    memory.pressures[secret_id] = min(
                        100, memory.pressures.get(secret_id, 0) + KEYWORD_MATCH_DELTA
                    )
                    triggered = True

    if not triggered:
        for secret_id, value in list(memory.pressures.items()):
            memory.pressures[secret_id] = max(0, value - DECAY_PER_ROUND)

    warnings: list[str] = []
    for secret in memory.secrets:
        secret_id = secret.get("secret_id", "")
        if not secret_id:
            continue
        pressure = memory.pressures.get(secret_id, 0)
        if pressure >= 80:
            warnings.append(
                f"关于「{secret.get('description','')[:30]}...」的秘密压力已达到临界点。"
            )

    pressure_text = format_pressure_warning(warnings)

    last_thoughts_section = ""
    if last_inner_thoughts:
        last_thoughts_section = (
            f"【我上一轮的内心想法】\n{last_inner_thoughts}\n"
            "（你可以保持这个想法，也可以根据新信息改变主意。）"
        )

    # Build the character prompt
    goals_list = "（无）"
    if goals:
        goals_list = "\n".join(
            f"- {g.get('goal_id', '')}: {g.get('description', '')}" for g in goals
        )
    prompt = CHARACTER_DECISION.format(
        character_name=char_id,
        pressure_warning=pressure_text,
        visible_actions=visible_text,
        scene_description=scene_description,
        last_thoughts_section=last_thoughts_section,
        goals_list=goals_list,
    )
    prompt += (
        "\n\n【角色稳定记忆】\n"
        f"{memory.stable or '（无）'}\n"
        "\n【角色工作记忆】\n"
        f"{memory.working or '（无）'}\n"
        "\n【公共广播新增】\n"
        f"{public_delta or '（无）'}\n"
    )

    # Add retry feedback if this is a retry
    if retry_feedback:
        prompt += (
            f"\n\n⚠️ 修正要求：你上次的回复存在问题：{retry_feedback}\n"
            "请确保你只使用你知道的信息重新决策。"
        )

    logger.info(
        "character.deciding",
        character=char_id,
        round=current_round,
        turn=current_turn,
        visible_actions_count=len(visible),
        has_pressure_warnings=bool(warnings),
    )

    # Layer 2: Prompt engineering — the prompt constrains information access
    system_msg = f"你是{char_id}。你必须完全代入角色，只基于你知道的信息做决策。"
    result = await call_llm(
        system_prompt=system_msg,
        user_message=prompt,
        response_format=None,
    )
    content = result.get("content", "") if isinstance(result, dict) else str(result)
    parsed = parse_memory_update(content)

    itype = parsed.interaction_type or ""
    if not itype:
        if parsed.spoken and parsed.action:
            itype = "composite"
        elif parsed.spoken:
            itype = "speak"
        elif parsed.action:
            itype = "action"
        else:
            itype = "speak"

    action_pack: ActionPack = {
        "character_id": char_id,
        "round": current_round,
        "turn": current_turn,
        "interaction_type": itype,
        "spoken_content": parsed.spoken or None,
        "action_content": parsed.action or None,
        "inner_reasoning": parsed.inner or "",
        "targets": parsed.targets,
    }

    # Update memory file
    if parsed.memory_summary:
        memory.working = parsed.memory_summary
    else:
        append_text = "\n".join(parsed.memory_append).strip()
        if append_text:
            memory.working = (memory.working + "\n" + append_text).strip()
    if parsed.self_eval:
        memory.self_eval = "\n".join(
            f"{item.get('goal_id', '')}: {item.get('status', '')} | {item.get('note', '')}"
            for item in parsed.self_eval
        ).strip()
        # Apply self-eval to goals
        for item in parsed.self_eval:
            gid = item.get("goal_id")
            status = item.get("status")
            if not gid or not status:
                continue
            for goal in memory.goals:
                if goal.get("goal_id") == gid:
                    goal["status"] = status
    save_memory(memory_path, memory)

    logger.info(
        "character.decided",
        character=char_id,
        interaction_type=action_pack["interaction_type"],
        targets=action_pack["targets"],
    )

    return action_pack
