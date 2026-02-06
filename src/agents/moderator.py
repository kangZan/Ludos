"""Moderator agent — scene management, objective recording, pacing control."""

import structlog

from src.agents.llm_client import call_llm
from src.config.prompts import (
    MODERATOR_ROUND_ASSESSMENT,
    MODERATOR_SCENE_ANNOUNCEMENT,
    MODERATOR_TURN_ORDER,
)
from src.models.types import ActionPack, CharacterDossier, ObjectiveFacts, SecretEntry, TaggedInfo
from src.tools.prompt_loader import load_conversion_prompt
from src.utils.errors import RuntimeWorkflowError
from src.utils.half_structured_parser import (
    parse_initialization,
    parse_round_assessment,
    parse_scene_announcement,
    parse_turn_order,
)
from src.utils.json_parser import extract_json

logger = structlog.get_logger(__name__)


async def parse_narrative(outline: str) -> dict:
    """Parse a narrative outline into structured objective facts and character dossiers.

    Uses the conversion prompt template from doc/ to transform free-form
    narrative text into the standardized JSON format.
    """
    system_prompt = load_conversion_prompt()
    logger.info("parsing_narrative", outline_length=len(outline))

    result = await call_llm(
        system_prompt=system_prompt,
        user_message=outline,
        temperature=0.0,
    )

    parsed = _extract_initialization_from_result(result)

    if not _is_valid_initialization(parsed):
        logger.warning("narrative_parse_retry", detail="missing sections")
        retry_message = (
            "请严格按半结构化格式输出（包含 [OBJECTIVE_FACTS] 与多个 [CHARACTER] 块），"
            "不要输出JSON。\n\n"
            f"{outline}"
        )
        result = await call_llm(
            system_prompt=system_prompt,
            user_message=retry_message,
            temperature=0.0,
        )
        parsed = _extract_initialization_from_result(result)

    if not _is_valid_initialization(parsed):
        parsed = _coerce_minimal_initialization(outline, parsed)

    logger.info(
        "narrative_parsed",
        num_characters=len(parsed.get("character_dossiers", [])),
    )
    return parsed


def _coerce_minimal_initialization(outline: str, raw: object) -> dict:
    """Build a minimal valid initialization payload from raw output."""
    summary = outline[:200]
    return {
        "purely_objective_facts": {
            "时空状态": summary or "未知",
            "物理状态": "未知",
            "交互基础": "可对话",
            "起始事件": "未知",
        },
        "ending_direction": "",
        "protagonists": [],
        "character_dossiers": [
            {
                "角色标识": "角色A",
                "核心身份认知": "我是角色A。我处于未知情境中。",
                "对此刻状况的私人理解": "我需要先观察环境和其他人。",
                "个人本轮目标": ["先确认局势", "避免暴露弱点"],
            }
        ],
        "_raw_output": str(raw),
    }


def build_dossiers_from_parsed(
    parsed: dict,
) -> tuple[ObjectiveFacts, dict[str, CharacterDossier]]:
    """Convert parsed initialization output into domain types.

    Returns:
        Tuple of (objective_facts, character_dossiers_dict).
    """
    facts_raw = parsed["purely_objective_facts"]
    objective_facts: ObjectiveFacts = {
        "时空状态": facts_raw["时空状态"],
        "物理状态": facts_raw["物理状态"],
        "交互基础": facts_raw["交互基础"],
        "起始事件": facts_raw["起始事件"],
    }

    dossiers: dict[str, CharacterDossier] = {}
    character_ids = [cd["角色标识"] for cd in parsed.get("character_dossiers", [])]
    public_info: list[TaggedInfo] = [
        {
            "content": f"{key}:{value}",
            "visibility": "公开",
            "source": "objective_facts",
            "known_by": character_ids,
        }
        for key, value in objective_facts.items()
    ]

    for cd in parsed["character_dossiers"]:
        char_id = cd["角色标识"]

        goals_raw = cd.get("个人本轮目标", [])
        goals = []
        for i, g in enumerate(goals_raw):
            goal_text = g if isinstance(g, str) else str(g)
            goals.append({
                "goal_id": f"{char_id}_goal_{i}",
                "description": goal_text,
                "status": "active",
            })

        # Build known_info from the dossier content
        known_info: list[TaggedInfo] = [
            *public_info,
            {
                "content": cd["核心身份认知"],
                "visibility": "私有",
                "source": "self_awareness",
                "known_by": [char_id],
            },
            {
                "content": cd["对此刻状况的私人理解"],
                "visibility": "私有",
                "source": "personal_analysis",
                "known_by": [char_id],
            },
        ]

        # Extract secrets (heuristic: private info containing sensitive keywords)
        secrets: list[SecretEntry] = _extract_secrets(char_id, cd)

        dossiers[char_id] = {
            "character_id": char_id,
            "core_identity": cd["核心身份认知"],
            "private_understanding": cd["对此刻状况的私人理解"],
            "goals": goals,
            "known_info": known_info,
            "secrets": secrets,
        }

    return objective_facts, dossiers


def _extract_secrets(char_id: str, cd: dict) -> list[SecretEntry]:
    """Extract potential secrets from a character dossier using heuristics.

    Looks for indicators of secret information in the private understanding.
    """
    secrets: list[SecretEntry] = []
    understanding = cd.get("对此刻状况的私人理解", "")

    secret_indicators = ["秘密", "不能让", "隐瞒", "不知道", "偷偷", "暗中", "私下"]
    for i, indicator in enumerate(secret_indicators):
        if indicator in understanding:
            # Extract a phrase around the indicator as keywords
            idx = understanding.find(indicator)
            context_start = max(0, idx - 10)
            context_end = min(len(understanding), idx + 20)
            context = understanding[context_start:context_end]

            keywords = [w for w in context.split() if len(w) >= 2]
            if not keywords:
                keywords = [indicator]

            secrets.append({
                "secret_id": f"{char_id}_secret_{i}",
                "description": context,
                "keywords": keywords,
                "is_revealed": False,
            })

    return secrets


async def announce_scene(
    objective_facts: ObjectiveFacts,
    previous_round_summary: str,
    environmental_events: list[str],
) -> dict:
    """Generate a scene announcement."""
    facts_str = "\n".join([f"{k}: {v}" for k, v in objective_facts.items()])
    events_str = "\n".join(environmental_events) if environmental_events else "无"

    prompt = MODERATOR_SCENE_ANNOUNCEMENT.format(
        objective_facts=facts_str,
        previous_round_summary=previous_round_summary or "这是第一轮，尚无交互历史。",
        environmental_events=events_str,
    )

    result = await call_llm(
        system_prompt="你是角色驱动推演系统的主持人。",
        user_message=prompt,
    )
    if isinstance(result, dict) and "scene_description" in result:
        return result
    content = _extract_content(result)
    return parse_scene_announcement(content)


async def determine_turn_order(
    scene_description: str,
    active_characters: list[str],
    previous_actions: list[ActionPack],
) -> list[str]:
    """Determine the turn order for this round."""
    if previous_actions:
        actions_str = "\n".join(
            f"- {a['character_id']}: {a.get('spoken_content','') or ''} {a.get('action_content','') or ''}"
            for a in previous_actions
        )
    else:
        actions_str = "无（第一轮）"

    prompt = MODERATOR_TURN_ORDER.format(
        scene_description=scene_description,
        active_characters=", ".join(active_characters),
        previous_actions=actions_str,
    )

    result = await call_llm(
        system_prompt="你是角色驱动推演系统的主持人。",
        user_message=prompt,
    )

    if isinstance(result, dict) and "turn_order" in result:
        return result.get("turn_order", active_characters)
    content = _extract_content(result)
    parsed = parse_turn_order(content)
    return parsed.get("turn_order") or active_characters


async def assess_round(
    round_actions: list[ActionPack],
    character_goals: dict[str, list[dict]],
    current_round: int,
    max_rounds: int,
    ending_direction: str,
) -> dict:
    """Assess the round's progress and pacing."""
    if round_actions:
        actions_str = "\n".join(
            f"- {a['character_id']}: {a.get('spoken_content','') or ''} {a.get('action_content','') or ''}"
            for a in round_actions
        )
    else:
        actions_str = "无"

    if character_goals:
        goals_str = "\n".join(
            f"- {cid}: {', '.join(g.get('goal_id','') for g in goals if g)}"
            for cid, goals in character_goals.items()
        )
    else:
        goals_str = "无"

    prompt = MODERATOR_ROUND_ASSESSMENT.format(
        round_actions=actions_str,
        character_goals=goals_str,
        current_round=current_round,
        max_rounds=max_rounds,
        ending_direction=ending_direction or "未指定",
    )

    result = await call_llm(
        system_prompt="你是角色驱动推演系统的主持人。",
        user_message=prompt,
    )
    if isinstance(result, dict) and "scene_summary" in result:
        return result
    content = _extract_content(result)
    return parse_round_assessment(content)


def _is_valid_initialization(parsed: dict) -> bool:
    if not isinstance(parsed, dict):
        return False
    facts = parsed.get("purely_objective_facts", {})
    dossiers = parsed.get("character_dossiers", [])
    if not isinstance(facts, dict) or not isinstance(dossiers, list):
        return False
    if not dossiers:
        return False
    return True


def _extract_content(result: object) -> str:
    if isinstance(result, dict) and "content" in result:
        return str(result.get("content") or "")
    return str(result or "")


def _extract_initialization_from_result(result: object) -> dict:
    if isinstance(result, dict) and "purely_objective_facts" in result:
        return result
    content = _extract_content(result)
    parsed = parse_initialization(content)
    if _is_valid_initialization(parsed):
        return parsed

    extracted = extract_json(content)
    if isinstance(extracted, dict) and "purely_objective_facts" in extracted:
        return extracted
    if isinstance(extracted, list):
        first_obj = next((item for item in extracted if isinstance(item, dict)), None)
        if first_obj and "purely_objective_facts" in first_obj:
            return first_obj

    return parsed
