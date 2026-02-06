"""Export graph visualization diagrams."""

from pathlib import Path

from src.graphs.orchestrator import build_orchestrator_graph
from src.utils.visualization import export_graph_mermaid, export_graph_png


def main() -> None:
    """Generate and export graph visualizations."""
    output_dir = Path("doc/v0.1.0")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Building orchestrator graph...")
    graph = build_orchestrator_graph()

    print("Exporting Mermaid diagram...")
    export_graph_mermaid(graph, output_dir / "graph.mmd")

    print("Exporting PNG diagram...")
    export_graph_png(graph, output_dir / "graph.png")

    print(f"Visualizations saved to {output_dir}/")


if __name__ == "__main__":
    main()
