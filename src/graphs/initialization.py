"""Initialization subgraph — parse narrative outline into structured data."""

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.moderator import build_dossiers_from_parsed, parse_narrative
from src.config.settings import settings
from src.graphs.state import DeductionState
from src.utils.character_memory import seed_memory_if_missing

logger = structlog.get_logger(__name__)


async def parse_outline_node(state: DeductionState) -> dict:
    """Parse the narrative outline into structured JSON."""
    outline = state["narrative_outline"]
    logger.info("initialization.parse_outline", outline_length=len(outline))

    parsed = await parse_narrative(outline)
    objective_facts, character_dossiers = build_dossiers_from_parsed(parsed)
    ending_direction = parsed.get("ending_direction") or ""
    protagonists = parsed.get("protagonists") or []

    character_ids = list(character_dossiers.keys())
    character_goals = {
        cid: list(dossier.get("goals", [])) for cid, dossier in character_dossiers.items()
    }
    character_secrets = {
        cid: list(dossier.get("secrets", [])) for cid, dossier in character_dossiers.items()
    }

    # Seed per-character memory files
    session_id = state.get("session_id", "default")
    memory_dir = f"data/characters/{session_id}"
    for cid, dossier in character_dossiers.items():
        goals = ", ".join([g["description"] for g in dossier.get("goals", [])])
        known = "\n".join([info["content"] for info in dossier.get("known_info", [])])
        stable_seed = (
            f"身份：{dossier['core_identity']}\n"
            f"私人理解：{dossier['private_understanding']}\n"
            f"目标：{goals}\n"
            f"已知信息：{known}"
        )
        seed_memory_if_missing(
            f"{memory_dir}/{cid}.mem.txt",
            stable_seed,
            goals=list(dossier.get("goals", [])),
            secrets=list(dossier.get("secrets", [])),
        )

    return {
        "objective_facts": objective_facts,
        "character_ids": character_ids,
        "ending_direction": ending_direction,
        "protagonists": protagonists,
        "last_inner_thoughts": {},
        "current_round": 0,
        "max_rounds": settings.max_rounds,
        "current_round_actions": [],
        "environmental_events": [],
        "is_deduction_complete": False,
        "end_reason": None,
    }


async def validate_structure_node(state: DeductionState) -> dict:
    """Validate that parsed dossiers have correct structure."""
    logger.info(
        "initialization.validated",
        num_characters=len(state.get("character_ids", [])),
        num_issues=0,
    )
    return {}


async def distribute_dossiers_node(state: DeductionState) -> dict:
    """Prepare initial scene description from objective facts."""
    facts = state["objective_facts"]
    scene = (
        f"【时空】{facts['时空状态']}\n"
        f"【环境】{facts['物理状态']}\n"
        f"【交互规则】{facts['交互基础']}\n"
        f"【起始事件】{facts['起始事件']}"
    )

    logger.info(
        "initialization.distributed",
        num_characters=len(state.get("character_ids", [])),
    )

    return {"current_scene": scene}


def build_initialization_graph() -> StateGraph:
    """Build the initialization subgraph."""
    graph = StateGraph(DeductionState)

    graph.add_node("parse_outline", parse_outline_node)
    graph.add_node("validate_structure", validate_structure_node)
    graph.add_node("distribute_dossiers", distribute_dossiers_node)

    graph.add_edge(START, "parse_outline")
    graph.add_edge("parse_outline", "validate_structure")
    graph.add_edge("validate_structure", "distribute_dossiers")
    graph.add_edge("distribute_dossiers", END)

    return graph
