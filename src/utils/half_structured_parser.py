"""Parse half-structured LLM outputs into usable dicts.

The format relies on explicit section headers like:
  [SECTION_NAME]
"""

from __future__ import annotations

import re


_SECTION_RE = re.compile(r"(?m)^[\[\【]?\s*(?P<name>[A-Z0-9_\-\s]+)\s*[\]\】]?\s*$")

_SECTION_ALIASES = {
    "OBJECTIVEFACTS": "OBJECTIVE_FACTS",
    "OBJECTIVEFACT": "OBJECTIVE_FACTS",
    "FACTS": "OBJECTIVE_FACTS",
    "CHAR": "CHARACTER",
    "CHARACTERS": "CHARACTER",
    "ENDINGDIRECTION": "ENDING_DIRECTION",
    "PROTAGONIST": "PROTAGONISTS",
    "PROTAGONISTS": "PROTAGONISTS",
    "SCENEDESCRIPTION": "SCENE_DESCRIPTION",
    "PLOTHINT": "PLOT_HINT",
    "TURNORDER": "TURN_ORDER",
    "REASONING": "REASONING",
    "SCENESUMMARY": "SCENE_SUMMARY",
    "GOALASSESSMENTS": "GOAL_ASSESSMENTS",
    "PACINGNOTES": "PACING_NOTES",
    "SUGGESTEDEVENTS": "SUGGESTED_EVENTS",
    "ENDINGDIRECTIONMET": "ENDING_DIRECTION_MET",
    "SHOULDEND": "SHOULD_END",
    "ENDREASON": "END_REASON",
}

_SECTION_ALIASES_CN = {
    "客观事实": "OBJECTIVE_FACTS",
    "客观信息": "OBJECTIVE_FACTS",
    "场景事实": "OBJECTIVE_FACTS",
    "角色": "CHARACTER",
    "角色档案": "CHARACTER",
    "角色信息": "CHARACTER",
    "结局方向": "ENDING_DIRECTION",
    "结局": "ENDING_DIRECTION",
    "主角": "PROTAGONISTS",
    "主角名单": "PROTAGONISTS",
    "场景描述": "SCENE_DESCRIPTION",
    "场景播报": "SCENE_DESCRIPTION",
    "剧情提示": "PLOT_HINT",
    "行动顺序": "TURN_ORDER",
    "回合评估": "SCENE_SUMMARY",
    "目标评估": "GOAL_ASSESSMENTS",
    "节奏提示": "PACING_NOTES",
    "建议事件": "SUGGESTED_EVENTS",
    "是否达成结局": "ENDING_DIRECTION_MET",
    "是否结束": "SHOULD_END",
    "结束原因": "END_REASON",
}
_FIELD_ALIASES = {
    "时空状态": "时空状态",
    "时间状态": "时空状态",
    "时间": "时空状态",
    "空间": "时空状态",
    "物理状态": "物理状态",
    "环境": "物理状态",
    "场景": "物理状态",
    "交互基础": "交互基础",
    "交互规则": "交互基础",
    "起始事件": "起始事件",
    "事件": "起始事件",
    "角色标识": "角色标识",
    "角色": "角色标识",
    "姓名": "角色标识",
    "核心身份认知": "核心身份认知",
    "身份认知": "核心身份认知",
    "身份": "核心身份认知",
    "对此刻状况的私人理解": "对此刻状况的私人理解",
    "私人理解": "对此刻状况的私人理解",
    "个人本轮目标": "个人本轮目标",
    "本轮目标": "个人本轮目标",
    "目标": "个人本轮目标",
}


def _split_sections(text: str) -> dict[str, str]:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return {}

    sections: dict[str, list[str]] = {}
    current_name: str | None = None

    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        header, remainder = _normalize_inline_header(raw)
        if header:
            current_name = header
            sections.setdefault(current_name, [])
            if remainder:
                sections[current_name].append(remainder)
            continue

        if current_name:
            sections[current_name].append(raw)

    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _parse_key_values(block: str) -> dict[str, str]:
    data: dict[str, str] = {}
    current_key: str | None = None
    lines = [line.strip() for line in (block or "").splitlines()]
    for line in lines:
        if not line:
            continue
        sep_match = re.split(r"[:：=＝]", line, maxsplit=1)
        if len(sep_match) == 2:
            key, value = sep_match
            key = _normalize_field(key.strip())
            value = value.strip()
            data[key] = value
            current_key = key
            continue
        if current_key:
            data[current_key] = f"{data[current_key]}\n{line}".strip()
    return data


def _parse_list(block: str) -> list[str]:
    items: list[str] = []
    for line in (block or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("-", "•", "*")):
            items.append(line[1:].strip())
            continue
        if "," in line:
            items.extend([chunk.strip() for chunk in line.split(",") if chunk.strip()])
        else:
            items.append(line)
    return [item for item in items if item]


def _parse_character_block(block: str) -> dict:
    lines = [line.strip() for line in (block or "").splitlines() if line.strip()]
    fields: dict[str, str] = {}
    goals: list[str] = []
    in_goals = False
    current_key: str | None = None

    for line in lines:
        if _normalize_field(_split_key(line)[0]) == "个人本轮目标":
            in_goals = True
            current_key = None
            if _has_kv_separator(line):
                _, value = _split_key(line)
                value = value.strip()
                if value:
                    goals.append(value)
            continue

        if in_goals and line.startswith(("-", "•", "*")):
            goals.append(line[1:].strip())
            continue

        if _has_kv_separator(line):
            key, value = _split_key(line)
            key = _normalize_field(key.strip())
            value = value.strip()
            fields[key] = value
            current_key = key
            in_goals = False
            continue

        if in_goals and goals:
            goals[-1] = f"{goals[-1]} {line}".strip()
            continue

        if current_key:
            fields[current_key] = f"{fields[current_key]}\n{line}".strip()

    if goals:
        fields["个人本轮目标"] = goals
    return fields


def parse_initialization(text: str) -> dict:
    """Parse narrative conversion output into initialization dict."""
    sections = _split_sections(text)
    facts_raw = _parse_key_values(sections.get("OBJECTIVE_FACTS", ""))
    facts = {
        "时空状态": facts_raw.get("时空状态", "未知"),
        "物理状态": facts_raw.get("物理状态", "未知"),
        "交互基础": facts_raw.get("交互基础", "未知"),
        "起始事件": facts_raw.get("起始事件", "未知"),
    }

    characters: list[dict] = []
    for block in _split_repeated_block(text, "CHARACTER"):
        for sub_block in _split_character_subblocks(block):
            fields = _parse_character_block(sub_block)
            if "角色标识" not in fields:
                continue
            if "个人本轮目标" not in fields:
                fields["个人本轮目标"] = []
            characters.append(fields)

    ending_direction = sections.get("ENDING_DIRECTION", "").strip()
    protagonists = _parse_list(sections.get("PROTAGONISTS", ""))

    return {
        "purely_objective_facts": facts,
        "character_dossiers": characters,
        "ending_direction": ending_direction,
        "protagonists": protagonists,
    }


def _split_repeated_block(text: str, header: str) -> list[str]:
    header = header.upper()
    blocks: list[str] = []
    current: list[str] = []
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        normalized, remainder = _normalize_inline_header(raw)
        if normalized == header:
            if current:
                blocks.append("\n".join(current).strip())
            current = []
            if remainder:
                current.append(remainder)
            continue
        if current is not None:
            current.append(raw)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def parse_scene_announcement(text: str) -> dict:
    sections = _split_sections(text)
    scene = sections.get("SCENE_DESCRIPTION", "").strip()
    plot_hint = sections.get("PLOT_HINT", "").strip()
    if not scene:
        scene = text.strip()
    return {"scene_description": scene, "plot_hint": plot_hint}


def parse_turn_order(text: str) -> dict:
    sections = _split_sections(text)
    order = _parse_list(sections.get("TURN_ORDER", ""))
    reasoning = sections.get("REASONING", "").strip()
    return {"turn_order": order, "reasoning": reasoning}


def parse_round_assessment(text: str) -> dict:
    sections = _split_sections(text)
    scene_summary = sections.get("SCENE_SUMMARY", "").strip()
    pacing_notes = sections.get("PACING_NOTES", "").strip()
    suggested_events = _parse_list(sections.get("SUGGESTED_EVENTS", ""))
    ending_met = _parse_bool(sections.get("ENDING_DIRECTION_MET", "false"))
    should_end = _parse_bool(sections.get("SHOULD_END", "false"))
    end_reason = sections.get("END_REASON", "").strip()

    goal_assessments = []
    raw_goals = sections.get("GOAL_ASSESSMENTS", "")
    for line in raw_goals.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("-", "•", "*")):
            line = line[1:].strip()
        parts = [p.strip() for p in line.split("|", 3)]
        if len(parts) < 4:
            continue
        character_id, goal_id, status, progress = parts
        goal_assessments.append({
            "character_id": character_id,
            "goal_id": goal_id,
            "status": status,
            "progress": progress,
        })

    return {
        "scene_summary": scene_summary,
        "goal_assessments": goal_assessments,
        "pacing_notes": pacing_notes,
        "suggested_events": suggested_events,
        "ending_direction_met": ending_met,
        "should_end": should_end,
        "end_reason": end_reason,
    }


def _parse_bool(text: str) -> bool:
    value = (text or "").strip().lower()
    return value in {"true", "yes", "y", "1", "是", "对"}


def _normalize_header(raw: str) -> str | None:
    match = _SECTION_RE.match(raw)
    if not match:
        return None
    name = match.group("name")
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "", name or "")
    cleaned = cleaned.upper().strip()
    if not cleaned:
        return None
    return _SECTION_ALIASES.get(cleaned, cleaned)


def _normalize_field(raw: str) -> str:
    key = re.sub(r"[：:\s]+", "", raw)
    return _FIELD_ALIASES.get(key, raw.strip())


def _normalize_inline_header(raw: str) -> tuple[str | None, str | None]:
    """Return (header, remainder) if the line defines a section header."""
    header = _normalize_header(raw)
    if header:
        return header, None

    # Try inline header with separator, e.g. "OBJECTIVE_FACTS: ..."
    parts = re.split(r"[:：]\s*", raw, maxsplit=1)
    if len(parts) == 2:
        candidate = _normalize_header(parts[0].strip())
        if candidate:
            return candidate, parts[1].strip()

    # Try CN header without brackets
    cleaned = re.sub(r"[【】\[\]\s]+", "", raw)
    if cleaned in _SECTION_ALIASES_CN:
        return _SECTION_ALIASES_CN[cleaned], None

    return None, None


def _has_kv_separator(line: str) -> bool:
    return any(sep in line for sep in (":", "：", "=", "＝"))


def _split_key(line: str) -> tuple[str, str]:
    parts = re.split(r"[:：=＝]", line, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return line.strip(), ""


def _split_character_subblocks(block: str) -> list[str]:
    lines = [line.strip() for line in (block or "").splitlines() if line.strip()]
    sub_blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if _normalize_field(_split_key(line)[0]) == "角色标识":
            if current:
                sub_blocks.append(current)
            current = [line]
            continue
        current.append(line)
    if current:
        sub_blocks.append(current)
    return ["\n".join(part).strip() for part in sub_blocks if part]
