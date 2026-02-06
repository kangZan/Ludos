"""Pydantic models for LLM structured output validation."""

from pydantic import BaseModel, Field


class ActionPackOutput(BaseModel):
    """Schema for validating character action output from LLM."""

    interaction_type: str = Field(
        description="One of: speak, action, composite"
    )
    spoken_content: str | None = Field(
        default=None,
        description="What the character actually says aloud",
    )
    action_content: str | None = Field(
        default=None,
        description="What the character physically does",
    )
    inner_reasoning: str = Field(
        description="Decision rationale or inner thoughts (private record only)",
    )
    targets: list[str] = Field(
        default_factory=list,
        description="Character IDs this action is directed at",
    )


class ObjectiveFactsOutput(BaseModel):
    """Schema for the purely_objective_facts section."""

    时空状态: str = Field(description="Time and spatial state")
    物理状态: str = Field(description="Physical state of the scene")
    交互基础: str = Field(description="Basic interaction rules")
    起始事件: str = Field(description="Triggering event")


class CharacterDossierOutput(BaseModel):
    """Schema for a single character dossier from initialization."""

    角色标识: str = Field(description="Character name or code")
    核心身份认知: str = Field(
        description="First-person self-awareness: who I am, current state"
    )
    对此刻状况的私人理解: str = Field(
        description="First-person paragraph: how I understand this situation"
    )
    个人本轮目标: list[str] = Field(
        description="First-person list of 1-3 immediate, self-interested goals"
    )


class InitializationOutput(BaseModel):
    """Schema for the complete initialization output."""

    purely_objective_facts: ObjectiveFactsOutput
    character_dossiers: list[CharacterDossierOutput]
    ending_direction: str | None = Field(
        default=None,
        description="Narrative ending direction or target outcome",
    )
    protagonists: list[str] = Field(
        default_factory=list,
        description="List of protagonist character IDs",
    )


class GoalAssessmentOutput(BaseModel):
    """Schema for moderator's per-goal assessment."""

    character_id: str = Field(description="Character ID")
    goal_id: str = Field(description="Goal ID")
    progress: str = Field(description="Qualitative progress description")
    status: str = Field(
        description="One of: active, achieved, failed, abandoned"
    )


class RoundAssessmentOutput(BaseModel):
    """Schema for moderator's round assessment."""

    scene_summary: str = Field(description="Brief objective summary of what happened")
    goal_assessments: list[GoalAssessmentOutput] = Field(
        description="Per-goal progress evaluations"
    )
    pacing_notes: str = Field(
        description="Notes on narrative pacing and flow"
    )
    suggested_events: list[str] = Field(
        default_factory=list,
        description="Optional environmental events to introduce",
    )
    ending_direction_met: bool = Field(
        default=False,
        description="Whether the narrative ending direction has been met",
    )
    should_end: bool = Field(
        default=False,
        description="Whether the deduction should end this round",
    )
    end_reason: str | None = Field(
        default=None,
        description="Reason for ending if should_end is True",
    )


class SceneAnnouncementOutput(BaseModel):
    """Schema for moderator's scene announcement."""

    scene_description: str = Field(
        description="Objective description of the current scene state"
    )
    plot_hint: str = Field(
        description="A subtle hint or prompt to push the narrative forward"
    )


class TurnOrderOutput(BaseModel):
    """Schema for moderator's turn order decision."""

    turn_order: list[str] = Field(
        description="Ordered list of character IDs for this round"
    )
    reasoning: str = Field(
        description="Brief explanation for the chosen order"
    )
