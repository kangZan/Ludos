"""Secret Pressure System — tracks and manages secret pressure accumulation (秘密压力值)."""

import structlog

from src.models.types import ActionPack, SecretEntry

logger = structlog.get_logger(__name__)

# Pressure increment values
KEYWORD_MATCH_DELTA = 10
DIRECT_ADDRESS_DELTA = 15
CONFLICT_ESCALATION_DELTA = 5
DECAY_PER_ROUND = 5


def calculate_pressure_deltas(
    round_actions: list[ActionPack],
    character_secrets: dict[str, list[SecretEntry]],
    current_pressures: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    """Calculate pressure changes for all characters based on round actions.

    Scans all spoken/action content for secret keywords and calculates
    pressure increments.

    Args:
        round_actions: All actions from the current round.
        character_secrets: All character secrets.
        current_pressures: Current pressure values.

    Returns:
        Updated pressure values dict (character_id -> secret_id -> new_value).
    """
    updated = {
        char_id: dict(secrets)
        for char_id, secrets in current_pressures.items()
    }

    # Collect all text from this round
    round_text_by_action: list[tuple[ActionPack, str]] = []
    for action in round_actions:
        text = (action.get("spoken_content") or "") + " " + (action.get("action_content") or "")
        text = text.strip()
        if text:
            round_text_by_action.append((action, text))

    triggered_any: dict[str, bool] = {char_id: False for char_id in character_secrets}

    for char_id, secrets in character_secrets.items():
        for secret in secrets:
            if secret.get("is_revealed", False):
                continue

            secret_id = secret["secret_id"]
            delta = 0

            for action, text in round_text_by_action:
                if action["character_id"] == char_id:
                    continue  # Skip own actions

                for keyword in secret.get("keywords", []):
                    if keyword in text:
                        # Base keyword match
                        base_delta = KEYWORD_MATCH_DELTA

                        # Extra pressure if speaker directly addresses the secret holder
                        if char_id in action.get("targets", []):
                            base_delta = DIRECT_ADDRESS_DELTA

                        delta += base_delta
                        triggered_any[char_id] = True

                        logger.debug(
                            "pressure.keyword_match",
                            secret_holder=char_id,
                            secret_id=secret_id,
                            keyword=keyword,
                            speaker=action["character_id"],
                            delta=base_delta,
                        )

            if delta > 0:
                current = updated.get(char_id, {}).get(secret_id, 0)
                updated.setdefault(char_id, {})[secret_id] = min(100, current + delta)

    # Apply decay for characters whose secrets were NOT triggered this round
    for char_id, was_triggered in triggered_any.items():
        if not was_triggered:
            for secret_id in updated.get(char_id, {}):
                current = updated[char_id][secret_id]
                updated[char_id][secret_id] = max(0, current - DECAY_PER_ROUND)

    return updated


def check_pressure_warnings(
    pressures: dict[str, dict[str, int]],
    character_secrets: dict[str, list[SecretEntry]],
    threshold: int,
) -> dict[str, list[str]]:
    """Generate warning messages for characters whose secrets are near threshold.

    Args:
        pressures: Current pressure values.
        character_secrets: Character secrets with details.
        threshold: The pressure threshold for triggering warnings.

    Returns:
        Dict of character_id -> list of warning messages.
    """
    warnings: dict[str, list[str]] = {}

    for char_id, secrets_pressure in pressures.items():
        char_warnings: list[str] = []
        secrets = character_secrets.get(char_id, [])
        for secret in secrets:
            if secret.get("is_revealed", False):
                continue

            secret_id = secret["secret_id"]
            pressure = secrets_pressure.get(secret_id, 0)

            if pressure >= threshold:
                char_warnings.append(
                    f"关于「{secret['description'][:30]}...」的秘密压力已达到临界点。"
                    f"对话正在触及你的敏感地带。你感到即将说漏嘴。"
                )
                logger.info(
                    "pressure.warning_triggered",
                    character=char_id,
                    secret_id=secret_id,
                    pressure=pressure,
                    threshold=threshold,
                )

        if char_warnings:
            warnings[char_id] = char_warnings

    return warnings
