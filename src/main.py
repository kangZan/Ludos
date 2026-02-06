"""CLI entry point for the Ludos narrative deduction system."""

import argparse
import asyncio
import sys
import uuid

import structlog

from src.config.settings import settings
from src.agents.llm_client import call_llm
from src.graphs.orchestrator import build_orchestrator_graph
from src.memory.checkpointer import get_checkpointer
from src.memory.interaction_store import InteractionStore
from src.tools import register_builtin_tools
from src.tools.text_formatter import (
    format_action_line,
    format_public_action_line,
    format_scene_header,
)
from src.utils.interaction_log_writer import InteractionLogWriter
from src.utils.logging import setup_logging
from src.utils.errors import ConfigurationError, RuntimeWorkflowError

logger = structlog.get_logger(__name__)


async def run_deduction(narrative_text: str, session_id: str | None = None) -> dict:
    """Run a complete narrative deduction session.

    Args:
        narrative_text: The narrative outline to process.
        session_id: Optional session ID for persistence.

    Returns:
        Final state with raw_interaction_log and polished_narrative.
    """
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    checkpointer = await get_checkpointer()
    graph = build_orchestrator_graph(checkpointer=checkpointer)

    store = InteractionStore(storage_dir="data/sessions")
    public_log_writer = InteractionLogWriter(f"logs/session_{session_id}.public.log")
    character_log_writers: dict[str, InteractionLogWriter] = {}

    def _safe_log_name(name: str) -> str:
        return "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in name)

    def _get_character_log_writer(char_id: str) -> InteractionLogWriter:
        writer = character_log_writers.get(char_id)
        if writer is not None:
            return writer
        safe_name = _safe_log_name(char_id)
        writer = InteractionLogWriter(f"logs/session_{session_id}_{safe_name}.raw.log")
        character_log_writers[char_id] = writer
        print(f"Raw log path ({char_id}): {writer.path}")
        return writer
    print(f"Public log path: {public_log_writer.path}")

    config = {"configurable": {"thread_id": session_id}}

    logger.info("session.starting", session_id=session_id)

    # Stream execution for real-time updates (auto-continue on interrupts)
    final_state: dict = {}
    input_payload: dict = {
        "narrative_outline": narrative_text,
        "session_id": session_id,
        "log_path": "",
        "public_log_path": str(public_log_writer.path),
    }
    seen_actions: set[tuple[int, int, str]] = set()
    last_scene = ""
    last_assessment_count = 0

    while True:
        interrupted = False
        async for event in graph.astream(
            input_payload,
            config=config,
            stream_mode="updates",
        ):
            if "__interrupt__" in event:
                logger.info("stream.interrupt_received")
                interrupted = True
                input_payload = {"__interrupt__": "continue"}
                break

            for node_name, update in event.items():
                if update is None or isinstance(update, tuple):
                    logger.debug("stream.update", node=node_name, keys=[])
                    continue
                logger.debug("stream.update", node=node_name, keys=list(update.keys()))

                # Ensure per-character log files exist once we know character ids.
                if "character_ids" in update:
                    for cid in update.get("character_ids", []):
                        _get_character_log_writer(cid)

                # Collect actions for the interaction store
                if "action_log" in update:
                    store.add_actions(update["action_log"])

                # Incremental console output for scene changes
                if "current_scene" in update:
                    scene = update.get("current_scene") or ""
                    if node_name == "distribute_dossiers":
                        last_scene = scene or last_scene
                        continue
                    if scene and scene != last_scene:
                        public_log_writer.append_line(format_scene_header(scene))
                        print("\n" + "-" * 60)
                        print("【场景播报】")
                        print(scene)
                        print("-" * 60 + "\n")
                        last_scene = scene

                # Incremental console output for new actions
                if "action_log" in update:
                    action_log = update.get("action_log", [])
                    if isinstance(action_log, list):
                        for action in action_log:
                            char_id = action.get("character_id", "unknown")
                            action_key = (
                                int(action.get("round", -1)),
                                int(action.get("turn", -1)),
                                str(char_id),
                            )
                            if action_key in seen_actions:
                                continue
                            seen_actions.add(action_key)

                            itype = action.get("interaction_type", "unknown")
                            spoken = action.get("spoken_content") or ""
                            act = action.get("action_content") or ""

                            _get_character_log_writer(char_id).append_line(
                                format_action_line(action)
                            )
                            public_log_writer.append_line(
                                format_public_action_line(action, None)
                            )
                            print(f"[{char_id}] {itype} {spoken} {act}".strip())

                # Incremental console output for round assessments
                if "round_assessments" in update:
                    assessments = update.get("round_assessments", [])
                    if isinstance(assessments, list) and len(assessments) > last_assessment_count:
                        new_assessments = assessments[last_assessment_count:]
                        for assessment in new_assessments:
                            round_number = assessment.get("round_number", "?")
                            summary = assessment.get("scene_summary", "")
                            pacing = assessment.get("pacing_notes", "")
                            print("\n" + "-" * 60)
                            print(f"【回合评估】第{round_number}轮")
                            if summary:
                                print(f"摘要：{summary}")
                            if pacing:
                                print(f"节奏：{pacing}")
                            print("-" * 60 + "\n")
                        last_assessment_count = len(assessments)

                final_state.update(update)

        if not interrupted:
            break

    # Save session data
    store.save_to_file(session_id)

    logger.info("session.completed", session_id=session_id)
    return final_state


def _health_check() -> int:
    """Run a lightweight health check for environment readiness."""
    issues: list[str] = []

    if not settings.llm_api_key:
        issues.append("LLM_API_KEY not set")

    if settings.llm_api_key:
        try:
            asyncio.run(_check_llm_connectivity())
        except Exception as exc:
            issues.append(f"LLM connectivity failed: {exc}")

    if issues:
        print("Health check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Health check OK")
    return 0


async def _check_llm_connectivity() -> None:
    """Validate LLM connectivity with a minimal call."""
    await call_llm(
        system_prompt="You are a health check endpoint.",
        user_message="ping",
        response_format=None,
        temperature=0.0,
        max_retries=0,
    )


def main() -> None:
    """CLI entry point."""
    setup_logging()
    register_builtin_tools()

    parser = argparse.ArgumentParser(
        description="Ludos - Character-driven narrative deduction system",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to narrative outline file (reads from stdin if not provided)",
    )
    parser.add_argument(
        "--session-id",
        help="Session ID for state persistence",
    )
    parser.add_argument(
        "--output",
        help="Output file path for polished narrative",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run health checks and exit",
    )

    args = parser.parse_args()

    if args.health:
        raise SystemExit(_health_check())

    # Read narrative text
    if args.input:
        from pathlib import Path

        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        narrative_text = input_path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        narrative_text = sys.stdin.read()
    else:
        print("Error: Please provide a narrative outline file or pipe text to stdin.", file=sys.stderr)
        print("Usage: ludos <input_file> [--output <output_file>]", file=sys.stderr)
        sys.exit(1)

    if not narrative_text.strip():
        print("Error: Empty input.", file=sys.stderr)
        sys.exit(1)

    # Run
    try:
        result = asyncio.run(run_deduction(narrative_text, args.session_id))
    except Exception as exc:
        logger.exception("run_failed")
        raise RuntimeWorkflowError("Deduction run failed") from exc

    # Output
    raw_log = result.get("raw_interaction_log", "")
    polished = result.get("polished_narrative", "")

    print("\n" + "=" * 60)
    print("【原始交互日志】")
    print("=" * 60)
    print(raw_log)

    print("\n" + "=" * 60)
    print("【润色叙事文本】")
    print("=" * 60)
    print(polished)

    if args.output:
        from pathlib import Path

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_content = (
            f"# 原始交互日志\n\n{raw_log}\n\n---\n\n# 润色叙事文本\n\n{polished}"
        )
        output_path.write_text(output_content, encoding="utf-8")
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except ConfigurationError as exc:
        logger.error("config_error", error=str(exc))
        raise SystemExit(2)
    except RuntimeWorkflowError as exc:
        logger.error("runtime_error", error=str(exc))
        raise SystemExit(3)
