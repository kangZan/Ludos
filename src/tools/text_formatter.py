"""Text formatting utilities for dossiers and interaction logs."""

from src.models.types import ActionPack, CharacterDossier, TaggedInfo


def format_dossier_for_character(dossier: CharacterDossier) -> dict[str, str]:
    """Render a character dossier as formatted text sections for prompt injection.

    Returns a dict with keys matching the character prompt template placeholders.
    """
    # Format known info with visibility tags
    known_lines: list[str] = []
    for info in dossier.get("known_info", []):
        tag = f"[{info['visibility']}]"
        source = f"（来源：{info['source']}）" if info.get("source") else ""
        known_lines.append(f"  {tag} {info['content']}{source}")

    # Format goals
    goals_lines: list[str] = []
    for g in dossier.get("goals", []):
        status_mark = ""
        if g["status"] == "achieved":
            status_mark = " [已达成]"
        elif g["status"] == "failed":
            status_mark = " [已失败]"
        goals_lines.append(f"  - {g['description']}{status_mark}")

    return {
        "character_name": dossier["character_id"],
        "core_identity": dossier["core_identity"],
        "private_understanding": dossier["private_understanding"],
        "goals_list": "\n".join(goals_lines) if goals_lines else "  （无明确目标）",
        "known_info": "\n".join(known_lines) if known_lines else "  （无额外已知信息）",
    }


def format_visible_actions(actions: list[ActionPack]) -> str:
    """Format a list of visible actions into readable text for character prompts."""
    if not actions:
        return "（尚无交互发生）"

    lines: list[str] = []
    for action in actions:
        parts: list[str] = [f"[{action['character_id']}]"]

        if action["interaction_type"] in ("speak", "composite"):
            if action.get("spoken_content"):
                parts.append(f'说："{action["spoken_content"]}"')

        if action["interaction_type"] in ("action", "composite"):
            if action.get("action_content"):
                parts.append(f"[动作] {action['action_content']}")

        lines.append(" ".join(parts))

    return "\n".join(lines)


def format_raw_interaction_log(
    actions: list[ActionPack],
    scene_description: str,
    character_dossiers: dict[str, CharacterDossier] | None = None,
) -> str:
    """Format a complete interaction log in the output format from requirements.

    Produces the "原始交互日志" format:
    [场景：...]
    [角色A-名字]（目标：...）[动作] ... [说话] ... [内心-私有]（...）
    """
    lines: list[str] = [f"[场景：{scene_description}]\n"]

    for action in actions:
        char_id = action["character_id"]
        goal_text = ""
        if character_dossiers and char_id in character_dossiers:
            goals = character_dossiers[char_id].get("goals", [])
            active_goals = [g["description"] for g in goals if g.get("status") == "active"]
            if active_goals:
                goal_text = f"（目标：{'；'.join(active_goals)}）"
        char_line = f"[角色-{char_id}]{goal_text}"

        if action["interaction_type"] in ("action", "composite"):
            if action.get("action_content"):
                char_line += f" [动作] {action['action_content']}"

        if action["interaction_type"] in ("speak", "composite"):
            if action.get("spoken_content"):
                char_line += f' [说话] "{action["spoken_content"]}"'

        if action.get("inner_reasoning"):
            char_line += f" [内心-私有]（{char_id}_{action['inner_reasoning']}）"

        lines.append(char_line)

    return "\n".join(lines)


def format_scene_header(scene_description: str) -> str:
    """Format the scene header line."""
    return f"[场景：{scene_description}]"


def format_action_line(
    action: ActionPack,
    character_dossiers: dict[str, CharacterDossier] | None = None,
) -> str:
    """Format a single action line in raw log style."""
    char_id = action["character_id"]
    goal_text = ""
    if character_dossiers and char_id in character_dossiers:
        goals = character_dossiers[char_id].get("goals", [])
        active_goals = [g["description"] for g in goals if g.get("status") == "active"]
        if active_goals:
            goal_text = f"（目标：{'；'.join(active_goals)}）"

    char_line = f"[角色-{char_id}]{goal_text}"

    if action["interaction_type"] in ("action", "composite"):
        if action.get("action_content"):
            char_line += f" [动作] {action['action_content']}"

    if action["interaction_type"] in ("speak", "composite"):
        if action.get("spoken_content"):
            char_line += f' [说话] "{action["spoken_content"]}"'

    if action.get("inner_reasoning"):
        char_line += f" [内心-私有]（{char_id}_{action['inner_reasoning']}）"

    return char_line


def format_public_action_line(
    action: ActionPack,
    character_dossiers: dict[str, CharacterDossier] | None = None,
) -> str:
    """Format a public action line without inner reasoning."""
    char_id = action["character_id"]
    goal_text = ""
    if character_dossiers and char_id in character_dossiers:
        goals = character_dossiers[char_id].get("goals", [])
        active_goals = [g["description"] for g in goals if g.get("status") == "active"]
        if active_goals:
            goal_text = f"（目标：{'；'.join(active_goals)}）"

    char_line = f"[角色-{char_id}]{goal_text}"

    if action["interaction_type"] in ("action", "composite"):
        if action.get("action_content"):
            char_line += f" [动作] {action['action_content']}"

    if action["interaction_type"] in ("speak", "composite"):
        if action.get("spoken_content"):
            char_line += f' [说话] "{action["spoken_content"]}"'

    return char_line


def format_pressure_warning(warnings: list[str]) -> str:
    """Format pressure warnings for injection into character prompt."""
    if not warnings:
        return ""

    header = "\n⚠️ 【秘密压力警告】\n"
    warning_text = "\n".join(f"  - {w}" for w in warnings)
    footer = "\n你感到秘密即将说漏。你是选择加倍隐瞒、巧妙转移话题，还是让某些东西泄露出来？这取决于你。\n"

    return header + warning_text + footer


def format_tagged_info(info_list: list[TaggedInfo]) -> str:
    """Format a list of tagged info items for display."""
    if not info_list:
        return "（无）"

    lines = []
    for info in info_list:
        tag = f"[{info['visibility']}]"
        source = f"（来源：{info['source']}）" if info.get("source") else ""
        lines.append(f"  {tag} {info['content']}{source}")

    return "\n".join(lines)
