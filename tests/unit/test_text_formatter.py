"""Tests for text formatting utilities."""

from src.models.types import ActionPack, CharacterDossier
from src.tools.text_formatter import (
    format_dossier_for_character,
    format_pressure_warning,
    format_raw_interaction_log,
    format_visible_actions,
)


class TestFormatDossierForCharacter:
    def test_formats_all_sections(self, sample_dossier_ned: CharacterDossier):
        result = format_dossier_for_character(sample_dossier_ned)
        assert result["character_name"] == "艾德"
        assert "我" in result["core_identity"]
        assert "目标" not in result["goals_list"] or "安抚" in result["goals_list"]
        assert result["known_info"]  # Not empty


class TestFormatVisibleActions:
    def test_empty_actions(self):
        result = format_visible_actions([])
        assert "尚无" in result

    def test_formats_speech(self, sample_action_ned: ActionPack):
        result = format_visible_actions([sample_action_ned])
        assert "艾德" in result
        assert "史坦尼斯" in result

    def test_formats_composite(self, sample_action_robert: ActionPack):
        result = format_visible_actions([sample_action_robert])
        assert "劳勃国王" in result
        assert "茶杯" in result
        assert "说了算" in result


class TestFormatRawInteractionLog:
    def test_includes_scene(
        self,
        sample_action_robert: ActionPack,
    ):
        result = format_raw_interaction_log([sample_action_robert], "皇宫偏殿")
        assert "皇宫偏殿" in result

    def test_includes_all_actions(
        self,
        sample_action_robert: ActionPack,
        sample_action_ned: ActionPack,
    ):
        result = format_raw_interaction_log(
            [sample_action_robert, sample_action_ned],
            "皇宫偏殿",
        )
        assert "劳勃国王" in result
        assert "艾德" in result
        assert "[动作]" in result
        assert "[说话]" in result
        assert "[内心-私有]" in result


class TestFormatPressureWarning:
    def test_empty_warnings(self):
        result = format_pressure_warning([])
        assert result == ""

    def test_formats_warning(self):
        result = format_pressure_warning(["秘密即将暴露"])
        assert "秘密" in result
        assert "警告" in result
