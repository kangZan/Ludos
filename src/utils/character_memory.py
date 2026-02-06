"""Character memory file helpers (half-structured text protocol)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CharacterMemory:
    """Parsed character memory file."""

    stable: str
    working: str
    last_public_offset: int
    self_eval: str
    goals: list[dict]
    secrets: list[dict]
    pressures: dict[str, int]


def load_memory(path: str | Path) -> CharacterMemory:
    """Load memory from a file. If missing, return empty memory."""
    p = Path(path)
    if not p.exists():
        return CharacterMemory(
            stable="",
            working="",
            last_public_offset=0,
            self_eval="",
            goals=[],
            secrets=[],
            pressures={},
        )

    text = p.read_text(encoding="utf-8")
    stable = _extract_block(text, "STABLE")
    working = _extract_block(text, "WORKING")
    self_eval = _extract_block(text, "SELF_EVAL")
    goals_block = _extract_block(text, "GOALS")
    secrets_block = _extract_block(text, "SECRETS")
    pressures_block = _extract_block(text, "PRESSURE")
    state = _extract_block(text, "STATE")

    last_offset = 0
    for line in state.splitlines():
        if line.startswith("last_public_offset="):
            try:
                last_offset = int(line.split("=", 1)[1].strip())
            except ValueError:
                last_offset = 0

    return CharacterMemory(
        stable=stable,
        working=working,
        last_public_offset=last_offset,
        self_eval=self_eval,
        goals=_parse_goals(goals_block),
        secrets=_parse_secrets(secrets_block),
        pressures=_parse_pressures(pressures_block),
    )


def save_memory(path: str | Path, memory: CharacterMemory) -> None:
    """Persist memory to file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "[STATE]\n"
        f"last_public_offset={memory.last_public_offset}\n\n"
        "[GOALS]\n"
        f"{_format_goals(memory.goals)}\n\n"
        "[SECRETS]\n"
        f"{_format_secrets(memory.secrets)}\n\n"
        "[PRESSURE]\n"
        f"{_format_pressures(memory.pressures)}\n\n"
        "[STABLE]\n"
        f"{memory.stable.strip()}\n\n"
        "[WORKING]\n"
        f"{memory.working.strip()}\n\n"
        "[SELF_EVAL]\n"
        f"{memory.self_eval.strip()}\n"
    )
    p.write_text(content, encoding="utf-8")


def seed_memory_if_missing(
    path: str | Path,
    stable_seed: str,
    goals: list[dict],
    secrets: list[dict],
) -> None:
    """Create a memory file if it doesn't exist."""
    p = Path(path)
    if p.exists():
        return
    pressures = {s.get("secret_id", ""): 0 for s in secrets if s.get("secret_id")}
    save_memory(
        p,
        CharacterMemory(
            stable=stable_seed,
            working="",
            last_public_offset=0,
            self_eval="",
            goals=goals,
            secrets=secrets,
            pressures=pressures,
        ),
    )


def _extract_block(text: str, name: str) -> str:
    start = text.find(f"[{name}]")
    if start == -1:
        return ""
    start += len(name) + 2
    end = text.find("[", start)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def _parse_goals(text: str) -> list[dict]:
    goals: list[dict] = []
    for line in text.splitlines():
        if not line.strip() or "|" not in line:
            continue
        goal_id, status, desc = (part.strip() for part in line.split("|", 2))
        goals.append({"goal_id": goal_id, "status": status, "description": desc})
    return goals


def _parse_secrets(text: str) -> list[dict]:
    secrets: list[dict] = []
    for line in text.splitlines():
        if not line.strip() or "|" not in line:
            continue
        secret_id, keywords, desc = (part.strip() for part in line.split("|", 2))
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        secrets.append(
            {
                "secret_id": secret_id,
                "keywords": kw_list,
                "description": desc,
                "is_revealed": False,
            }
        )
    return secrets


def _parse_pressures(text: str) -> dict[str, int]:
    pressures: dict[str, int] = {}
    for line in text.splitlines():
        if not line.strip() or "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            pressures[key.strip()] = int(value.strip())
        except ValueError:
            pressures[key.strip()] = 0
    return pressures


def _format_goals(goals: list[dict]) -> str:
    return "\n".join(
        f"{g.get('goal_id','')}|{g.get('status','active')}|{g.get('description','')}"
        for g in goals
    ).strip()


def _format_secrets(secrets: list[dict]) -> str:
    return "\n".join(
        f"{s.get('secret_id','')}|{','.join(s.get('keywords', []))}|{s.get('description','')}"
        for s in secrets
    ).strip()


def _format_pressures(pressures: dict[str, int]) -> str:
    return "\n".join(f"{k}={v}" for k, v in pressures.items()).strip()


def load_goals_map(memory_dir: str, character_ids: list[str]) -> dict[str, list[dict]]:
    """Load goals for each character from memory files."""
    goals_map: dict[str, list[dict]] = {}
    for cid in character_ids:
        mem = load_memory(Path(memory_dir) / f"{cid}.mem.txt")
        goals_map[cid] = list(mem.goals)
    return goals_map
