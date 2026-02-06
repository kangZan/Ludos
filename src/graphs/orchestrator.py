"""Top-level orchestrator graph — connects initialization, deduction loop, and polishing."""

import structlog
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.graphs.deduction_loop import (
    announce_scene_node,
    assess_round_node,
    character_turn_node,
    check_end_node,
    determine_turn_order_node,
    route_after_action,
    route_end,
)
from src.graphs.initialization import (
    distribute_dossiers_node,
    parse_outline_node,
    validate_structure_node,
)
from src.graphs.polishing import (
    literary_polish_node,
    prepare_raw_log_node,
    quality_check_node,
)
from src.graphs.state import DeductionState
from src.tools.text_formatter import format_raw_interaction_log

logger = structlog.get_logger(__name__)


async def review_dossiers_node(state: DeductionState) -> dict:
    """Human-in-the-loop: pause for user to review character dossiers."""
    logger.info(
        "orchestrator.review_skipped",
        num_characters=len(state.get("character_ids", [])),
    )
    return {}


async def prepare_polishing_node(state: DeductionState) -> dict:
    """Prepare raw interaction log for polishing stage."""
    raw_log = ""
    log_path = state.get("log_path", "")
    if log_path:
        from pathlib import Path

        path = Path(log_path)
        if path.exists():
            raw_log = path.read_text(encoding="utf-8")

    if not raw_log:
        raw_log = format_raw_interaction_log(
            actions=state.get("action_log", []),
            scene_description=state.get("current_scene", ""),
            character_dossiers=None,
        )

    logger.info("orchestrator.prepare_polishing", log_length=len(raw_log))

    return {"raw_interaction_log": raw_log}


async def polish_wrapper_node(state: DeductionState) -> dict:
    """Wrapper to run polishing with DeductionState."""
    from src.agents.polisher import polish_narrative

    polished = await polish_narrative(
        raw_log=state.get("raw_interaction_log", ""),
        memory_dir=f"data/characters/{state.get('session_id','default')}",
        scene_info=state.get("current_scene", ""),
    )

    return {"polished_narrative": polished}


def build_orchestrator_graph(
    checkpointer: InMemorySaver | None = None,
) -> CompiledStateGraph:
    """Build and compile the top-level orchestration graph.

    The graph connects three stages:
    1. Initialization: parse outline -> validate -> distribute dossiers -> human review
    2. Deduction Loop: announce scene -> turn order -> character turns -> assess -> check end
    3. Polishing: prepare raw log -> literary polish

    Args:
        checkpointer: Optional checkpointer for state persistence.

    Returns:
        Compiled graph ready for invocation.
    """
    graph = StateGraph(DeductionState)

    # --- Stage 1: Initialization ---
    graph.add_node("parse_outline", parse_outline_node)
    graph.add_node("validate_structure", validate_structure_node)
    graph.add_node("distribute_dossiers", distribute_dossiers_node)
    graph.add_node("review_dossiers", review_dossiers_node)

    # --- Stage 2: Deduction Loop ---
    graph.add_node("announce_scene", announce_scene_node)
    graph.add_node("determine_turn_order", determine_turn_order_node)
    graph.add_node("character_turn", character_turn_node)
    graph.add_node("assess_round", assess_round_node)
    graph.add_node("check_end", check_end_node)

    # --- Stage 3: Polishing ---
    graph.add_node("prepare_polishing", prepare_polishing_node)
    graph.add_node("polish_narrative", polish_wrapper_node)

    # --- Edges: Stage 1 ---
    graph.add_edge(START, "parse_outline")
    graph.add_edge("parse_outline", "validate_structure")
    graph.add_edge("validate_structure", "distribute_dossiers")
    graph.add_edge("distribute_dossiers", "review_dossiers")

    # --- Transition: Stage 1 -> Stage 2 ---
    graph.add_edge("review_dossiers", "announce_scene")

    # --- Edges: Stage 2 (Deduction Loop) ---
    graph.add_edge("announce_scene", "determine_turn_order")
    graph.add_edge("determine_turn_order", "character_turn")

    graph.add_conditional_edges(
        "character_turn",
        route_after_action,
        {
            "next_character": "character_turn",
            "round_complete": "assess_round",
        },
    )

    graph.add_edge("assess_round", "check_end")

    graph.add_conditional_edges(
        "check_end",
        route_end,
        {
            "continue": "announce_scene",
            "end": "prepare_polishing",
        },
    )

    # --- Edges: Stage 3 ---
    graph.add_edge("prepare_polishing", "polish_narrative")
    graph.add_edge("polish_narrative", END)

    # --- Compile ---
    if checkpointer is None:
        checkpointer = InMemorySaver()

    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("orchestrator.compiled")
    return compiled
