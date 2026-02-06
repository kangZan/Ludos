"""Tests for the secret pressure tracking system."""

from src.models.types import ActionPack, CharacterDossier
from src.tools.pressure_tracker import (
    DIRECT_ADDRESS_DELTA,
    KEYWORD_MATCH_DELTA,
    calculate_pressure_deltas,
    check_pressure_warnings,
)


class TestCalculatePressureDeltas:
    def test_keyword_increases_pressure(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """When someone mentions a secret keyword, pressure increases."""
        action: ActionPack = {
            "character_id": "劳勃国王",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "琼恩·艾林到底怎么死的？",
            "action_content": None,
            "inner_reasoning": "",
            "targets": ["艾德"],
        }

        pressures = {"艾德": {"艾德_secret_0": 0}, "劳勃国王": {}}

        updated = calculate_pressure_deltas(
            round_actions=[action],
            character_secrets={
                cid: dossier["secrets"] for cid, dossier in sample_all_dossiers.items()
            },
            current_pressures=pressures,
        )

        # Ned's secret pressure should increase (keyword "琼恩" and "艾林" match)
        assert updated["艾德"]["艾德_secret_0"] > 0

    def test_direct_address_higher_pressure(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """Directly addressing the secret holder causes more pressure."""
        action_targeted: ActionPack = {
            "character_id": "劳勃国王",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "艾林的信里写了什么？",
            "action_content": None,
            "inner_reasoning": "",
            "targets": ["艾德"],
        }

        action_general: ActionPack = {
            "character_id": "劳勃国王",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "艾林的信里写了什么？",
            "action_content": None,
            "inner_reasoning": "",
            "targets": [],  # Not targeting Ned directly
        }

        pressures = {"艾德": {"艾德_secret_0": 0}, "劳勃国王": {}}

        secrets = {cid: dossier["secrets"] for cid, dossier in sample_all_dossiers.items()}
        targeted_result = calculate_pressure_deltas(
            [action_targeted], secrets, pressures
        )
        general_result = calculate_pressure_deltas(
            [action_general], secrets, pressures
        )

        assert targeted_result["艾德"]["艾德_secret_0"] >= general_result["艾德"]["艾德_secret_0"]

    def test_no_pressure_from_own_actions(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """A character's own mention of keywords doesn't increase their pressure."""
        action: ActionPack = {
            "character_id": "艾德",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "我想起了琼恩·艾林...",
            "action_content": None,
            "inner_reasoning": "",
            "targets": [],
        }

        pressures = {"艾德": {"艾德_secret_0": 0}, "劳勃国王": {}}

        updated = calculate_pressure_deltas(
            [action],
            {cid: dossier["secrets"] for cid, dossier in sample_all_dossiers.items()},
            pressures,
        )

        assert updated["艾德"]["艾德_secret_0"] == 0

    def test_decay_when_no_trigger(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        """Pressure decays when no keywords are triggered."""
        action: ActionPack = {
            "character_id": "劳勃国王",
            "round": 2,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "今天天气不错",
            "action_content": None,
            "inner_reasoning": "",
            "targets": [],
        }

        pressures = {"艾德": {"艾德_secret_0": 30}, "劳勃国王": {}}

        updated = calculate_pressure_deltas(
            [action],
            {cid: dossier["secrets"] for cid, dossier in sample_all_dossiers.items()},
            pressures,
        )

        assert updated["艾德"]["艾德_secret_0"] < 30


class TestCheckPressureWarnings:
    def test_warning_at_threshold(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        pressures = {"艾德": {"艾德_secret_0": 80}, "劳勃国王": {}}
        warnings = check_pressure_warnings(
            pressures,
            {cid: dossier["secrets"] for cid, dossier in sample_all_dossiers.items()},
            threshold=80,
        )

        assert "艾德" in warnings
        assert len(warnings["艾德"]) == 1

    def test_no_warning_below_threshold(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        pressures = {"艾德": {"艾德_secret_0": 50}, "劳勃国王": {}}
        warnings = check_pressure_warnings(
            pressures,
            {cid: dossier["secrets"] for cid, dossier in sample_all_dossiers.items()},
            threshold=80,
        )

        assert "艾德" not in warnings

    def test_no_warning_for_revealed_secret(
        self,
        sample_all_dossiers: dict[str, CharacterDossier],
    ):
        # Mark secret as revealed
        dossiers = dict(sample_all_dossiers)
        ned = dict(dossiers["艾德"])
        ned["secrets"] = [dict(ned["secrets"][0])]
        ned["secrets"][0]["is_revealed"] = True
        dossiers["艾德"] = ned  # type: ignore[assignment]

        pressures = {"艾德": {"艾德_secret_0": 100}}
        warnings = check_pressure_warnings(
            pressures,
            {cid: dossier["secrets"] for cid, dossier in dossiers.items()},
            threshold=80,
        )

        assert "艾德" not in warnings
