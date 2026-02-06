"""Domain types for the narrative deduction system."""

from typing import Literal, TypedDict


class TaggedInfo(TypedDict):
    """A piece of information with visibility tagging (认知红绿灯)."""

    content: str
    visibility: Literal["私有", "公开"]
    source: str
    known_by: list[str]


class SecretEntry(TypedDict):
    """A character's secret with pressure tracking metadata."""

    secret_id: str
    description: str
    keywords: list[str]
    is_revealed: bool


class CharacterGoal(TypedDict):
    """An immediate, self-interested goal for a character."""

    goal_id: str
    description: str
    status: Literal["active", "achieved", "failed", "abandoned"]


class CharacterDossier(TypedDict):
    """Complete character dossier — first-person perspective."""

    character_id: str
    core_identity: str  # 核心身份认知 (first-person "我")
    private_understanding: str  # 对此刻状况的私人理解 (first-person)
    goals: list[CharacterGoal]  # 个人本轮目标
    known_info: list[TaggedInfo]  # 已知信息（标注[私有]/[公开]）
    secrets: list[SecretEntry]  # 该角色持有的秘密


class ActionPack(TypedDict):
    """A character's composite action output for one turn."""

    character_id: str
    round: int
    turn: int
    interaction_type: Literal["speak", "action", "composite"]
    spoken_content: str | None
    action_content: str | None
    inner_reasoning: str  # 仅内部记录，不可对外暴露
    targets: list[str]  # 该行动针对的角色ID列表


class ObjectiveFacts(TypedDict):
    """Purely objective facts about the scene — zero subjective content."""

    时空状态: str
    物理状态: str
    交互基础: str
    起始事件: str


class GoalAssessment(TypedDict):
    """Per-character goal progress assessment by the moderator."""

    character_id: str
    goal_id: str
    progress: str  # qualitative description
    status: Literal["active", "achieved", "failed", "abandoned"]


class RoundAssessment(TypedDict):
    """Moderator's assessment of a single round."""

    round_number: int
    scene_summary: str
    goal_assessments: list[GoalAssessment]
    pacing_notes: str
    suggested_events: list[str]
    ending_direction_met: bool
