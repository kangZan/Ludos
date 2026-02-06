"""Half-structured text protocol for character memory updates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemoryUpdate:
    interaction_type: str
    spoken: str
    action: str
    inner: str
    targets: list[str]
    memory_append: list[str]
    memory_summary: str
    self_eval: list[dict]


def parse_memory_update(text: str) -> MemoryUpdate:
    """Parse the model output into interaction + memory updates."""
    interaction_block = _extract_block(text, "INTERACTION")
    memory_append_block = _extract_block(text, "MEMORY_APPEND")
    memory_summary_block = _extract_block(text, "MEMORY_SUMMARY")
    self_eval_block = _extract_block(text, "SELF_EVAL")

    itype = _extract_field(interaction_block, "交互类型")
    spoken = _extract_field(interaction_block, "说话")
    action = _extract_field(interaction_block, "动作")
    inner = _extract_field(interaction_block, "内心")
    targets_raw = _extract_field(interaction_block, "针对")
    targets = [t.strip() for t in targets_raw.split(",") if t.strip()] if targets_raw else []

    memory_append = [
        line.lstrip("- ").strip()
        for line in memory_append_block.splitlines()
        if line.strip()
    ]

    self_eval: list[dict] = []
    for line in self_eval_block.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            continue
        goal_id, rest = line.split(":", 1)
        status_note = rest.split("|", 1)
        status = status_note[0].strip()
        note = status_note[1].strip() if len(status_note) > 1 else ""
        self_eval.append({"goal_id": goal_id.strip(), "status": status, "note": note})

    return MemoryUpdate(
        interaction_type=itype or "",
        spoken=spoken or "",
        action=action or "",
        inner=inner or "",
        targets=targets,
        memory_append=memory_append,
        memory_summary=memory_summary_block.strip(),
        self_eval=self_eval,
    )


def _extract_block(text: str, name: str) -> str:
    marker = f"[{name}]"
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    end = text.find("[", start)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def _extract_field(block: str, field: str) -> str:
    for line in block.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""
