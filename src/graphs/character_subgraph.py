"""Character decision subgraph — build context, decide, validate."""

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.character import decide_action
from src.graphs.state import CharacterNodeState
from src.utils.validators import validate_action_pack, validate_no_info_leakage

logger = structlog.get_logger(__name__)

MAX_RETRIES = 2


async def build_context_node(state: CharacterNodeState) -> dict:
    """Prepare the character's context — this is a pass-through for clarity."""
    logger.info(
        "character_subgraph.build_context",
        character=state["character_id"],
        num_visible_actions=len(state.get("visible_actions", [])),
    )
    return {}


async def decide_action_node(state: CharacterNodeState) -> dict:
    """Have the character make a decision via LLM."""
    action = await decide_action(
        character_id=state["character_id"],
        scene_description=state["scene_description"],
        all_round_actions=state.get("visible_actions", []),
        last_inner_thoughts=state.get("last_inner_thoughts", ""),
        current_round=0,  # Will be set by parent
        current_turn=0,
        retry_feedback=state.get("retry_feedback", ""),
        public_log_path=None,
        memory_dir="data/characters",
    )

    return {"action": action}


async def validate_action_node(state: CharacterNodeState) -> dict:
    """Validate the action for structure and information leakage.

    Layer 3 of the Cognitive Traffic Light: post-hoc validation.
    """
    action = state.get("action")  # type: ignore[arg-type]
    if action is None:
        return {"validation_passed": False, "retry_feedback": "No action produced."}

    # Structural validation
    struct_errors = validate_action_pack(action)
    if struct_errors:
        logger.warning(
            "character_subgraph.struct_errors",
            character=state["character_id"],
            errors=struct_errors,
        )
        return {
            "validation_passed": False,
            "retry_feedback": f"结构错误: {'; '.join(struct_errors)}",
        }

    # Information leakage detection
    leakage = validate_no_info_leakage(
        action=action,
        actor_dossier=state["character_dossier"],
        all_dossiers=state.get("all_dossiers", {}),
    )

    if leakage:
        logger.warning(
            "character_subgraph.info_leakage",
            character=state["character_id"],
            violations=leakage,
        )
        return {
            "validation_passed": False,
            "retry_feedback": f"信息泄露: {'; '.join(leakage)}",
        }

    return {"validation_passed": True, "retry_feedback": ""}


def route_validation(state: CharacterNodeState) -> str:
    """Route based on validation result."""
    if state.get("validation_passed", False):
        return "end"

    retry_count = state.get("retry_count", 0)
    if retry_count >= MAX_RETRIES:
        logger.error(
            "character_subgraph.max_retries",
            character=state["character_id"],
        )
        return "end"  # Accept with issues after max retries

    return "retry"


def build_character_subgraph() -> StateGraph:
    """Build the character decision subgraph."""

    # Extend CharacterNodeState for internal use
    class InternalCharacterState(CharacterNodeState, total=False):
        action: dict
        validation_passed: bool

    graph = StateGraph(InternalCharacterState)

    graph.add_node("build_context", build_context_node)
    graph.add_node("decide_action", decide_action_node)
    graph.add_node("validate_action", validate_action_node)

    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "decide_action")
    graph.add_edge("decide_action", "validate_action")

    graph.add_conditional_edges(
        "validate_action",
        route_validation,
        {
            "end": END,
            "retry": "decide_action",
        },
    )

    return graph
