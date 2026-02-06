"""Tests for end condition detection."""

from src.models.types import CharacterDossier
from src.tools.end_detector import check_end_conditions


class TestCheckEndConditions:
    def test_max_rounds_exceeded(self, sample_all_dossiers: dict[str, CharacterDossier]):
        goals = {
            cid: dossier["goals"] for cid, dossier in sample_all_dossiers.items()
        }
        should_end, reason = check_end_conditions(
            current_round=20,
            max_rounds=20,
            character_goals=goals,
            round_assessment=None,
            protagonists=[],
        )
        assert should_end is True
        assert reason == "max_rounds_exceeded"

    def test_not_ended_within_rounds(self, sample_all_dossiers: dict[str, CharacterDossier]):
        goals = {
            cid: dossier["goals"] for cid, dossier in sample_all_dossiers.items()
        }
        should_end, reason = check_end_conditions(
            current_round=5,
            max_rounds=20,
            character_goals=goals,
            round_assessment=None,
            protagonists=[],
        )
        assert should_end is False
        assert reason is None

    def test_moderator_ends(self, sample_all_dossiers: dict[str, CharacterDossier]):
        assessment = {"should_end": True, "end_reason": "predetermined_ending_reached"}
        goals = {
            cid: dossier["goals"] for cid, dossier in sample_all_dossiers.items()
        }
        should_end, reason = check_end_conditions(
            current_round=3,
            max_rounds=20,
            character_goals=goals,
            round_assessment=assessment,
            protagonists=[],
        )
        assert should_end is True
        assert reason == "predetermined_ending_reached"

    def test_all_goals_resolved(self):
        goals = {
            "A": [{"goal_id": "g1", "description": "目标", "status": "achieved"}],
            "B": [{"goal_id": "g2", "description": "目标", "status": "failed"}],
        }
        should_end, reason = check_end_conditions(
            current_round=3,
            max_rounds=20,
            character_goals=goals,
            round_assessment=None,
            protagonists=[],
        )
        assert should_end is True
        assert reason == "all_goals_resolved"

    def test_ending_direction_met(self, sample_all_dossiers: dict[str, CharacterDossier]):
        assessment = {"ending_direction_met": True}
        goals = {
            cid: dossier["goals"] for cid, dossier in sample_all_dossiers.items()
        }
        should_end, reason = check_end_conditions(
            current_round=2,
            max_rounds=20,
            character_goals=goals,
            round_assessment=assessment,
            protagonists=[],
        )
        assert should_end is True
        assert reason == "ending_direction_met"

    def test_protagonist_goals_resolved(self):
        goals = {
            "Hero": [{"goal_id": "g1", "description": "目标", "status": "achieved"}],
            "Other": [{"goal_id": "g2", "description": "目标", "status": "active"}],
        }
        should_end, reason = check_end_conditions(
            current_round=3,
            max_rounds=20,
            character_goals=goals,
            round_assessment=None,
            protagonists=["Hero"],
        )
        assert should_end is True
        assert reason == "protagonist_Hero_goals_resolved"
