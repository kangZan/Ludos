"""Turn order management for the deduction loop."""

import structlog

from src.agents.moderator import determine_turn_order as moderator_determine_order
from src.models.types import ActionPack

logger = structlog.get_logger(__name__)


async def determine_turn_order(
    scene_description: str,
    active_character_ids: list[str],
    previous_round_actions: list[ActionPack],
) -> list[str]:
    """Determine the character turn order for a round.

    For round 1, uses default order. For subsequent rounds, delegates
    to the moderator agent for intelligent ordering.

    Args:
        scene_description: Current scene state.
        active_character_ids: IDs of characters in the scene.
        previous_round_actions: Actions from the previous round.

    Returns:
        Ordered list of character IDs.
    """
    if not previous_round_actions:
        # First round: use default order
        logger.info("turn_manager.first_round", order=active_character_ids)
        return list(active_character_ids)

    # Subsequent rounds: let moderator decide based on narrative flow
    order = await moderator_determine_order(
        scene_description=scene_description,
        active_characters=active_character_ids,
        previous_actions=previous_round_actions,
    )

    # Keep only active characters, preserve order
    active_set = set(active_character_ids)
    order = [cid for cid in order if cid in active_set]

    # Validate that all active characters are included
    order_set = set(order)
    for char_id in active_character_ids:
        if char_id not in order_set:
            order.append(char_id)

    logger.info("turn_manager.order_determined", order=order)
    return order
