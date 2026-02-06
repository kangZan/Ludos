"""Deduction loop subgraph — the core simulation loop.

Flow:
    announce_scene -> determine_turn_order -> dispatch_next_character
    -> character_turn -> collect_action -> route_after_action
    -> (loop back or) assess_round -> check_end
    -> (loop back to announce_scene or END)
"""

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.character import decide_action
from src.agents.moderator import announce_scene, assess_round
from src.graphs.state import DeductionState
from src.tools.end_detector import check_end_conditions
from src.tools.turn_manager import determine_turn_order
from src.utils.character_memory import load_goals_map, load_memory

logger = structlog.get_logger(__name__)


# --- Node Functions ---


async def announce_scene_node(state: DeductionState) -> dict:
    """Moderator announces the current scene state."""
    current_round = state.get("current_round", 0) + 1

    # Summarize previous round
    prev_actions = state.get("current_round_actions", [])
    if prev_actions:
        summary_parts = []
        for a in prev_actions:
            parts = [f"{a['character_id']}"]
            if a.get("spoken_content"):
                parts.append(f'说："{a["spoken_content"][:50]}"')
            if a.get("action_content"):
                parts.append(f"[{a['action_content'][:50]}]")
            summary_parts.append(" ".join(parts))
        prev_summary = "\n".join(summary_parts)
    else:
        prev_summary = ""

    result = await announce_scene(
        objective_facts=state["objective_facts"],
        previous_round_summary=prev_summary,
        environmental_events=state.get("environmental_events", []),
    )

    scene = result.get("scene_description", state.get("current_scene", ""))

    logger.info("deduction.scene_announced", round=current_round)

    return {
        "current_round": current_round,
        "current_scene": scene,
        "current_round_actions": [],  # Reset for new round
        "current_turn": 0,
        "environmental_events": [],  # Clear consumed events
    }


async def determine_turn_order_node(state: DeductionState) -> dict:
    """Determine which character acts in what order this round."""
    active_chars = list(state.get("character_ids", []))

    # Get previous round's actions for ordering decisions
    prev_actions = state.get("action_log", [])
    prev_round = state.get("current_round", 1) - 1
    prev_round_actions = [a for a in prev_actions if a.get("round") == prev_round]

    order = await determine_turn_order(
        scene_description=state["current_scene"],
        active_character_ids=active_chars,
        previous_round_actions=prev_round_actions,
    )

    logger.info("deduction.turn_order", order=order)
    return {"turn_order": order}


async def character_turn_node(state: DeductionState) -> dict:
    """Execute one character's turn — they decide and act autonomously.

    This is where the "next character determines outcome" pattern is key:
    each character sees previous actions as INTENTIONS, and their REACTION
    determines the outcome.
    """
    turn_idx = state["current_turn"]
    turn_order = state["turn_order"]

    if turn_idx >= len(turn_order):
        return {}

    char_id = turn_order[turn_idx]
    # Get last inner thoughts
    last_thoughts = state.get("last_inner_thoughts", {}).get(char_id, "")

    # Character makes their decision
    # Note: filter_visible_actions is called inside decide_action
    memory_dir = f"data/characters/{state.get('session_id','default')}"
    memory = load_memory(f"{memory_dir}/{char_id}.mem.txt")
    action = await decide_action(
        character_id=char_id,
        scene_description=state["current_scene"],
        all_round_actions=state.get("current_round_actions", []),
        last_inner_thoughts=last_thoughts,
        current_round=state["current_round"],
        current_turn=turn_idx,
        public_log_path=state.get("public_log_path"),
        memory_dir=memory_dir,
        goals=memory.goals,
    )

    # Update last inner thoughts
    updated_thoughts = dict(state.get("last_inner_thoughts", {}))
    updated_thoughts[char_id] = action.get("inner_reasoning", "")

    logger.info(
        "deduction.character_acted",
        character=char_id,
        round=state["current_round"],
        turn=turn_idx,
        type=action["interaction_type"],
    )

    return {
        "current_round_actions": state.get("current_round_actions", []) + [action],
        "action_log": [action],  # Accumulated via add reducer
        "last_inner_thoughts": updated_thoughts,
        "current_turn": turn_idx + 1,
    }


def route_after_action(state: DeductionState) -> str:
    """Route: more characters to act, or round is complete."""
    turn_idx = state.get("current_turn", 0)
    turn_order = state.get("turn_order", [])

    if turn_idx < len(turn_order):
        return "next_character"
    return "round_complete"


async def assess_round_node(state: DeductionState) -> dict:
    """Moderator assesses the round's progress."""
    # Moderator only sees public information; do not read private goals.
    char_goals: dict[str, list[dict]] = {}

    public_actions = []
    for action in state.get("current_round_actions", []):
        public_actions.append(
            {
                "character_id": action.get("character_id"),
                "interaction_type": action.get("interaction_type"),
                "spoken_content": action.get("spoken_content"),
                "action_content": action.get("action_content"),
                "targets": action.get("targets", []),
            }
        )

    assessment = await assess_round(
        round_actions=public_actions,
        character_goals=char_goals,
        current_round=state["current_round"],
        max_rounds=state["max_rounds"],
        ending_direction=state.get("ending_direction", ""),
    )

    # Collect any suggested environmental events
    events = assessment.get("suggested_events", [])

    logger.info(
        "deduction.round_assessed",
        round=state["current_round"],
        suggested_events=len(events),
    )

    return {
        "round_assessments": [{
            "round_number": state["current_round"],
            "scene_summary": assessment.get("scene_summary", ""),
            "goal_assessments": assessment.get("goal_assessments", []),
            "pacing_notes": assessment.get("pacing_notes", ""),
            "suggested_events": events,
            "ending_direction_met": assessment.get("ending_direction_met", False),
        }],
        "environmental_events": events,
    }


async def check_end_node(state: DeductionState) -> dict:
    """Check if the deduction should end."""
    assessments = state.get("round_assessments", [])
    latest_assessment = assessments[-1] if assessments else None

    should_end, reason = check_end_conditions(
        current_round=state["current_round"],
        max_rounds=state["max_rounds"],
        character_goals=load_goals_map(
            f"data/characters/{state.get('session_id','default')}",
            state.get("character_ids", []),
        ),
        round_assessment=latest_assessment,
        protagonists=state.get("protagonists", []),
    )

    if should_end:
        logger.info("deduction.ending", reason=reason, round=state["current_round"])

    return {
        "is_deduction_complete": should_end,
        "end_reason": reason,
    }


def route_end(state: DeductionState) -> str:
    """Route: continue to next round or end deduction."""
    if state.get("is_deduction_complete", False):
        return "end"
    return "continue"


# --- Graph Builder ---


def build_deduction_loop_graph() -> StateGraph:
    """Build the deduction loop subgraph."""
    graph = StateGraph(DeductionState)

    # Add nodes
    graph.add_node("announce_scene", announce_scene_node)
    graph.add_node("determine_turn_order", determine_turn_order_node)
    graph.add_node("character_turn", character_turn_node)
    graph.add_node("assess_round", assess_round_node)
    graph.add_node("check_end", check_end_node)

    # Entry
    graph.add_edge(START, "announce_scene")
    graph.add_edge("announce_scene", "determine_turn_order")
    graph.add_edge("determine_turn_order", "character_turn")

    # Character turn loop
    graph.add_conditional_edges(
        "character_turn",
        route_after_action,
        {
            "next_character": "character_turn",
            "round_complete": "assess_round",
        },
    )

    # Round completion flow
    graph.add_edge("assess_round", "check_end")

    # End check
    graph.add_conditional_edges(
        "check_end",
        route_end,
        {
            "continue": "announce_scene",
            "end": END,
        },
    )

    return graph
