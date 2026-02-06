"""Data validation and information leakage detection."""

import structlog

from src.models.types import ActionPack, CharacterDossier

logger = structlog.get_logger(__name__)


def validate_dossier_structure(dossier: CharacterDossier) -> list[str]:
    """Validate a character dossier has all required fields and correct format.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []

    if not dossier.get("character_id"):
        errors.append("Missing character_id")
    if not dossier.get("core_identity"):
        errors.append("Missing core_identity")
    if not dossier.get("private_understanding"):
        errors.append("Missing private_understanding")
    if not dossier.get("goals"):
        errors.append("Missing or empty goals")
    if dossier.get("known_info") is None:
        errors.append("Missing known_info")

    # Verify first-person perspective
    identity = dossier.get("core_identity", "")
    understanding = dossier.get("private_understanding", "")
    if "我" not in identity and "我" not in understanding:
        errors.append("Dossier must use first-person perspective (我)")

    return errors


def validate_action_pack(action: ActionPack) -> list[str]:
    """Validate an action pack structure.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []

    if not action.get("character_id"):
        errors.append("Missing character_id")

    itype = action.get("interaction_type")
    if itype not in ("speak", "action", "composite"):
        errors.append(f"Invalid interaction_type: {itype}")

    if itype in ("speak", "composite") and not action.get("spoken_content"):
        errors.append(f"interaction_type={itype} requires spoken_content")

    if itype in ("action", "composite") and not action.get("action_content"):
        errors.append(f"interaction_type={itype} requires action_content")

    if not action.get("inner_reasoning"):
        errors.append("Missing inner_reasoning")

    return errors


def validate_no_info_leakage(
    action: ActionPack,
    actor_dossier: CharacterDossier,
    all_dossiers: dict[str, CharacterDossier],
) -> list[str]:
    """Check if an action references information the character shouldn't know.

    Scans the action's spoken and action content for keywords from other
    characters' unrevealed secrets, and verifies whether the acting character
    has legitimate access to that information.

    Returns:
        List of violation descriptions. Empty if no leakage detected.
    """
    violations: list[str] = []
    action_text = (action.get("spoken_content") or "") + (action.get("action_content") or "")

    if not action_text:
        return violations

    actor_id = actor_dossier["character_id"]

    for other_id, other_dossier in all_dossiers.items():
        if other_id == actor_id:
            continue

        for secret in other_dossier.get("secrets", []):
            if secret.get("is_revealed", False):
                continue

            for keyword in secret.get("keywords", []):
                if keyword not in action_text:
                    continue

                # Check if the actor legitimately knows this keyword
                actor_knows = any(
                    keyword in info["content"]
                    for info in actor_dossier.get("known_info", [])
                    if info["visibility"] == "公开"
                    or actor_id in info.get("known_by", [])
                )

                if not actor_knows:
                    violations.append(
                        f"Character '{actor_id}' references keyword "
                        f"'{keyword}' from {other_id}'s secret "
                        f"'{secret['secret_id']}' without access"
                    )
                    logger.warning(
                        "info_leakage_detected",
                        actor=actor_id,
                        keyword=keyword,
                        secret_owner=other_id,
                    )

    return violations
