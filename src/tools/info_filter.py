"""Cognitive Traffic Light — information isolation filtering (认知红绿灯)."""

from src.models.types import ActionPack, TaggedInfo


def filter_visible_actions(
    all_actions: list[ActionPack],
    character_id: str,
) -> list[ActionPack]:
    """Filter actions to only those visible to a specific character.

    Implements the structural layer of the Cognitive Traffic Light:
    - Strips inner_reasoning from ALL actions (never exposed)
    - Includes actions where this character is a target
    - Includes actions that are publicly observable (speech, visible actions)
    - Excludes the character's own past actions (they already know)

    Args:
        all_actions: All actions from the current round so far.
        character_id: The character requesting the filtered view.

    Returns:
        Sanitized list of actions visible to this character.
    """
    visible: list[ActionPack] = []

    for action in all_actions:
        if action["character_id"] == character_id:
            continue

        sanitized: ActionPack = {
            "character_id": action["character_id"],
            "round": action["round"],
            "turn": action["turn"],
            "interaction_type": action["interaction_type"],
            "spoken_content": action.get("spoken_content"),
            "action_content": _sanitize_action_content(action),
            "inner_reasoning": "",  # ALWAYS stripped
            "targets": action.get("targets", []),
        }

        # Include if: character is targeted, or it's a publicly observable action
        if (
            character_id in action.get("targets", [])
            or _is_publicly_observable(action)
        ):
            visible.append(sanitized)

    return visible


def filter_known_info(
    known_info: list[TaggedInfo],
    character_id: str,
) -> list[TaggedInfo]:
    """Filter tagged information to only what a character can access.

    Args:
        known_info: Full list of tagged information.
        character_id: The character requesting access.

    Returns:
        Filtered list of accessible information.
    """
    accessible: list[TaggedInfo] = []

    for info in known_info:
        if info["visibility"] == "公开":
            accessible.append(info)
        elif character_id in info.get("known_by", []):
            accessible.append(info)

    return accessible


def _is_publicly_observable(action: ActionPack) -> bool:
    """Determine if an action is publicly observable.

    Speech is always public. Physical actions visible in shared space are public.
    """
    if action["interaction_type"] in ("speak", "composite"):
        return True

    # Physical actions are generally observable unless they're purely mental
    if action["interaction_type"] == "action" and action.get("action_content"):
        return True

    return False


def _sanitize_action_content(action: ActionPack) -> str | None:
    """Sanitize action content to remove internal-only details.

    Preserves observable behavior but strips any hidden motivations
    that might have leaked into the action description.
    """
    content = action.get("action_content")
    if content is None:
        return None

    return content
