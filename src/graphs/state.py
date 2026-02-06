"""LangGraph state definitions with custom reducers."""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import add_messages

from src.models.types import ActionPack, CharacterDossier, ObjectiveFacts, RoundAssessment


class DeductionState(TypedDict):
    """Top-level state for the entire deduction workflow."""

    # --- Stage 1: Initialization output ---
    narrative_outline: str
    session_id: str
    objective_facts: ObjectiveFacts
    character_ids: list[str]
    ending_direction: str
    protagonists: list[str]

    # --- Deduction loop control ---
    current_round: int
    max_rounds: int
    current_scene: str
    turn_order: list[str]
    current_turn: int

    # --- Interaction records (accumulating via add reducer) ---
    action_log: Annotated[list[ActionPack], operator.add]
    current_round_actions: list[ActionPack]


    # --- Character inner state (persisted across rounds) ---
    last_inner_thoughts: dict[str, str]

    # --- Round assessments ---
    round_assessments: Annotated[list[RoundAssessment], operator.add]
    environmental_events: list[str]

    # --- End control ---
    is_deduction_complete: bool
    end_reason: str | None

    # --- Outputs ---
    raw_interaction_log: str
    polished_narrative: str
    log_path: str
    public_log_path: str

    # --- LangGraph message history ---
    messages: Annotated[list, add_messages]


class CharacterNodeState(TypedDict):
    """State passed to a character subgraph for one turn."""

    character_id: str
    character_dossier: CharacterDossier
    scene_description: str
    visible_actions: list[ActionPack]
    pressure_warnings: list[str]
    last_inner_thoughts: str
    all_dossiers: dict[str, CharacterDossier]
    retry_count: int
    retry_feedback: str


class PolishingState(TypedDict):
    """State for the polishing subgraph."""

    raw_log: str
    scene_info: str
    polished_narrative: str
    memory_dir: str
