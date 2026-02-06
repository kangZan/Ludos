"""Tests for data validation and info leakage detection."""

from src.models.types import ActionPack, CharacterDossier
from src.utils.validators import (
    validate_action_pack,
    validate_dossier_structure,
    validate_no_info_leakage,
)


class TestValidateDossierStructure:
    def test_valid_dossier(self, sample_dossier_ned: CharacterDossier):
        errors = validate_dossier_structure(sample_dossier_ned)
        assert errors == []

    def test_missing_character_id(self):
        dossier = {
            "character_id": "",
            "core_identity": "我是某人",
            "private_understanding": "我理解一切",
            "goals": [{"goal_id": "g1", "description": "目标", "status": "active"}],
            "known_info": [],
            "secrets": [],
        }
        errors = validate_dossier_structure(dossier)  # type: ignore[arg-type]
        assert any("character_id" in e for e in errors)

    def test_missing_first_person(self):
        dossier = {
            "character_id": "test",
            "core_identity": "他是一个人",
            "private_understanding": "他理解一切",
            "goals": [{"goal_id": "g1", "description": "目标", "status": "active"}],
            "known_info": [],
            "secrets": [],
        }
        errors = validate_dossier_structure(dossier)  # type: ignore[arg-type]
        assert any("first-person" in e.lower() or "我" in e for e in errors)


class TestValidateActionPack:
    def test_valid_speak(self, sample_action_ned: ActionPack):
        errors = validate_action_pack(sample_action_ned)
        assert errors == []

    def test_valid_composite(self, sample_action_robert: ActionPack):
        errors = validate_action_pack(sample_action_robert)
        assert errors == []

    def test_speak_without_content(self):
        action: ActionPack = {
            "character_id": "test",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "",
            "action_content": None,
            "inner_reasoning": "thinking",
            "targets": [],
        }
        errors = validate_action_pack(action)
        assert any("spoken_content" in e for e in errors)

    def test_invalid_interaction_type(self):
        action: ActionPack = {
            "character_id": "test",
            "round": 1,
            "turn": 0,
            "interaction_type": "invalid",  # type: ignore[typeddict-item]
            "spoken_content": None,
            "action_content": None,
            "inner_reasoning": "thinking",
            "targets": [],
        }
        errors = validate_action_pack(action)
        assert any("interaction_type" in e for e in errors)


class TestInfoLeakageDetection:
    def test_no_leakage_with_legitimate_info(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """Robert talking about public info should not trigger leakage."""
        action: ActionPack = {
            "character_id": "劳勃国王",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "史坦尼斯逃回了龙石岛！",
            "action_content": None,
            "inner_reasoning": "",
            "targets": ["艾德"],
        }
        violations = validate_no_info_leakage(
            action, sample_all_dossiers["劳勃国王"], sample_all_dossiers
        )
        assert violations == []

    def test_detects_leakage(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """Robert referencing Ned's secret keywords should trigger leakage."""
        action: ActionPack = {
            "character_id": "劳勃国王",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "瑟曦王后到底做了什么？琼恩的信说了什么？",
            "action_content": None,
            "inner_reasoning": "",
            "targets": ["艾德"],
        }
        violations = validate_no_info_leakage(
            action, sample_all_dossiers["劳勃国王"], sample_all_dossiers
        )
        # Robert shouldn't know about the letter, so this is leakage
        assert len(violations) > 0

    def test_no_self_leakage(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """Ned referencing his own secret keywords is not leakage."""
        action: ActionPack = {
            "character_id": "艾德",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "我必须小心那封信的事...",
            "action_content": None,
            "inner_reasoning": "琼恩的信太危险了",
            "targets": [],
        }
        violations = validate_no_info_leakage(
            action, sample_all_dossiers["艾德"], sample_all_dossiers
        )
        assert violations == []
