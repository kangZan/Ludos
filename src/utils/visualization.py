"""Graph visualization export utilities."""

from pathlib import Path

import structlog
from langgraph.graph.state import CompiledStateGraph

logger = structlog.get_logger(__name__)


def export_graph_mermaid(graph: CompiledStateGraph, output_path: str | Path) -> None:
    """Export the graph as a Mermaid diagram text file.

    Args:
        graph: Compiled LangGraph graph.
        output_path: Path for the output file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        mermaid_str = graph.get_graph().draw_mermaid()
        output_path.write_text(mermaid_str, encoding="utf-8")
        logger.info("visualization.mermaid_exported", path=str(output_path))
    except Exception:
        logger.exception("visualization.mermaid_export_failed")


def export_graph_png(graph: CompiledStateGraph, output_path: str | Path) -> None:
    """Export the graph as a PNG image.

    Requires graphviz or uses Mermaid rendering. Falls back to Mermaid text
    if image generation is not available.

    Args:
        graph: Compiled LangGraph graph.
        output_path: Path for the output PNG.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        output_path.write_bytes(png_bytes)
        logger.info("visualization.png_exported", path=str(output_path))
    except Exception:
        logger.warning("visualization.png_failed_fallback_mermaid")
        mermaid_path = output_path.with_suffix(".mmd")
        export_graph_mermaid(graph, mermaid_path)
