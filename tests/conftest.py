"""Shared test fixtures."""

import pytest

from src.models.types import (
    ActionPack,
    CharacterDossier,
    CharacterGoal,
    ObjectiveFacts,
    SecretEntry,
    TaggedInfo,
)


@pytest.fixture
def sample_objective_facts() -> ObjectiveFacts:
    return {
        "时空状态": "夜晚，皇宫的偏殿内。",
        "物理状态": "室内烛火照明。国王劳勃与艾德公爵站在一张地图前。",
        "交互基础": "二人可正常对话。",
        "起始事件": "劳勃国王刚刚抱怨了史坦尼斯逃回龙石岛。",
    }


@pytest.fixture
def sample_dossier_robert() -> CharacterDossier:
    return {
        "character_id": "劳勃国王",
        "core_identity": "我是七国国王。我现在喝醉了，感到愤怒和失望。",
        "private_understanding": "史坦尼斯的举动简直是公然违抗。艾德是我最信任的老友。",
        "goals": [
            CharacterGoal(
                goal_id="劳勃国王_goal_0",
                description="向艾德宣泄我对史坦尼斯的不满",
                status="active",
            ),
            CharacterGoal(
                goal_id="劳勃国王_goal_1",
                description="确保艾德会站在我这边",
                status="active",
            ),
        ],
        "known_info": [
            TaggedInfo(
                content="我是七国国王，掌握王权",
                visibility="公开",
                source="common_knowledge",
                known_by=["劳勃国王", "艾德"],
            ),
            TaggedInfo(
                content="史坦尼斯逃回了龙石岛",
                visibility="公开",
                source="common_knowledge",
                known_by=["劳勃国王", "艾德"],
            ),
        ],
        "secrets": [],
    }


@pytest.fixture
def sample_dossier_ned() -> CharacterDossier:
    return {
        "character_id": "艾德",
        "core_identity": "我是北方总督，国王的老友。我怀揣着一个致命的秘密。",
        "private_understanding": "劳勃喝醉了。琼恩·艾林的死不正常，我手里的秘密让一切更加危险。",
        "goals": [
            CharacterGoal(
                goal_id="艾德_goal_0",
                description="安抚劳勃但不做明确承诺",
                status="active",
            ),
            CharacterGoal(
                goal_id="艾德_goal_1",
                description="在不暴露秘密的前提下搜集宫廷信息",
                status="active",
            ),
        ],
        "known_info": [
            TaggedInfo(
                content="我是北方总督，劳勃的老友",
                visibility="公开",
                source="common_knowledge",
                known_by=["劳勃国王", "艾德"],
            ),
            TaggedInfo(
                content="琼恩·艾林死前寄给我一封指控王后瑟曦的信",
                visibility="私有",
                source="private_letter",
                known_by=["艾德"],
            ),
        ],
        "secrets": [
            SecretEntry(
                secret_id="艾德_secret_0",
                description="琼恩·艾林的秘密信件指控王后",
                keywords=["琼恩", "艾林", "信", "瑟曦", "王后"],
                is_revealed=False,
            ),
        ],
    }


@pytest.fixture
def sample_all_dossiers(
    sample_dossier_robert: CharacterDossier,
    sample_dossier_ned: CharacterDossier,
) -> dict[str, CharacterDossier]:
    return {
        "劳勃国王": sample_dossier_robert,
        "艾德": sample_dossier_ned,
    }


@pytest.fixture
def sample_action_robert() -> ActionPack:
    return {
        "character_id": "劳勃国王",
        "round": 1,
        "turn": 0,
        "interaction_type": "composite",
        "spoken_content": "这个家，还是我说了算。看看史坦尼斯那个叛徒！",
        "action_content": "将茶杯重重放下",
        "inner_reasoning": "我要让艾德知道我有多愤怒，他必须支持我",
        "targets": ["艾德"],
    }


@pytest.fixture
def sample_action_ned() -> ActionPack:
    return {
        "character_id": "艾德",
        "round": 1,
        "turn": 1,
        "interaction_type": "speak",
        "spoken_content": "陛下，史坦尼斯或许有自己的考量。我们应当冷静。",
        "action_content": None,
        "inner_reasoning": "我不能让劳勃冲动行事，但也不能暴露琼恩的信",
        "targets": ["劳勃国王"],
    }
