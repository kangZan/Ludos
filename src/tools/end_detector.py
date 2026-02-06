"""End-of-deduction condition detection."""

import structlog

from src.models.types import CharacterGoal

logger = structlog.get_logger(__name__)


def check_end_conditions(
    current_round: int,
    max_rounds: int,
    character_goals: dict[str, list[CharacterGoal]],
    round_assessment: dict | None,
    protagonists: list[str] | None = None,
) -> tuple[bool, str | None]:
    """Check whether the deduction should end.

    Evaluates three criteria:
    1. Moderator assessment indicates ending
    2. All active characters' goals are resolved
    3. Max rounds exceeded

    Args:
        current_round: The current round number.
        max_rounds: Maximum allowed rounds.
        character_goals: All character goals.
        round_assessment: Latest round assessment from moderator.

    Returns:
        Tuple of (should_end, reason).
    """
    # 1. Check ending direction reached
    if round_assessment and round_assessment.get("ending_direction_met"):
        logger.info("end_detector.ending_direction_met")
        return True, "ending_direction_met"

    # 2. Check moderator assessment
    if round_assessment and round_assessment.get("should_end"):
        reason = round_assessment.get("end_reason", "moderator_decision")
        logger.info("end_detector.moderator_end", reason=reason)
        return True, reason

    # 3. Check if protagonist goals are resolved
    if protagonists:
        for char_id in protagonists:
            goals = character_goals.get(char_id, [])
            if _goals_resolved(goals):
                logger.info("end_detector.protagonist_goals_resolved", character=char_id)
                return True, f"protagonist_{char_id}_goals_resolved"
    else:
        # Fallback: all goals resolved
        all_resolved = True
        for goals in character_goals.values():
            if not _goals_resolved(goals):
                all_resolved = False
                break

        if all_resolved and character_goals:
            logger.info("end_detector.all_goals_resolved")
            return True, "all_goals_resolved"

    # 4. Check max rounds
    if current_round >= max_rounds:
        logger.info("end_detector.max_rounds", current=current_round, max=max_rounds)
        return True, "max_rounds_exceeded"

    return False, None


def _goals_resolved(goals: list[CharacterGoal]) -> bool:
    if not goals:
        return False
    return all(goal.get("status") != "active" for goal in goals)
