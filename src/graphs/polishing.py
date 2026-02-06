"""Polishing subgraph — converts raw interaction log to literary narrative."""

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.polisher import polish_narrative
from src.graphs.state import PolishingState

logger = structlog.get_logger(__name__)


async def prepare_raw_log_node(state: PolishingState) -> dict:
    """Prepare and validate the raw log for polishing."""
    raw_log = state.get("raw_log", "")

    if not raw_log.strip():
        logger.warning("polishing.empty_log")
        return {"raw_log": "（无交互记录）"}

    logger.info("polishing.prepared", log_length=len(raw_log))
    return {}


async def literary_polish_node(state: PolishingState) -> dict:
    """Call the polishing agent to generate literary narrative."""
    polished = await polish_narrative(
        raw_log=state["raw_log"],
        memory_dir=state.get("memory_dir", ""),
        scene_info=state.get("scene_info", ""),
    )

    return {"polished_narrative": polished}


async def quality_check_node(state: PolishingState) -> dict:
    """Verify the polished output covers all interactions from the raw log."""
    raw_log = state.get("raw_log", "")
    polished = state.get("polished_narrative", "")

    if not polished.strip():
        logger.error("polishing.empty_output")
        return {"polished_narrative": f"（润色失败，原始日志如下）\n\n{raw_log}"}

    logger.info(
        "polishing.quality_checked",
        raw_length=len(raw_log),
        polished_length=len(polished),
        expansion_ratio=len(polished) / max(len(raw_log), 1),
    )

    return {}


def build_polishing_graph() -> StateGraph:
    """Build the polishing subgraph."""
    graph = StateGraph(PolishingState)

    graph.add_node("prepare_raw_log", prepare_raw_log_node)
    graph.add_node("literary_polish", literary_polish_node)
    graph.add_node("quality_check", quality_check_node)

    graph.add_edge(START, "prepare_raw_log")
    graph.add_edge("prepare_raw_log", "literary_polish")
    graph.add_edge("literary_polish", "quality_check")
    graph.add_edge("quality_check", END)

    return graph
