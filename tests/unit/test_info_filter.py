"""Tests for the cognitive traffic light — information isolation filtering."""

from src.models.types import ActionPack, TaggedInfo
from src.tools.info_filter import filter_known_info, filter_visible_actions


class TestFilterVisibleActions:
    def test_strips_inner_reasoning(self, sample_action_robert: ActionPack):
        visible = filter_visible_actions([sample_action_robert], "艾德")
        assert len(visible) == 1
        assert visible[0]["inner_reasoning"] == ""

    def test_includes_targeted_actions(self, sample_action_robert: ActionPack):
        visible = filter_visible_actions([sample_action_robert], "艾德")
        assert len(visible) == 1
        assert visible[0]["character_id"] == "劳勃国王"

    def test_excludes_own_actions(self, sample_action_robert: ActionPack):
        visible = filter_visible_actions([sample_action_robert], "劳勃国王")
        assert len(visible) == 0

    def test_includes_public_speech(self):
        action: ActionPack = {
            "character_id": "角色A",
            "round": 1,
            "turn": 0,
            "interaction_type": "speak",
            "spoken_content": "大家好",
            "action_content": None,
            "inner_reasoning": "我在试探",
            "targets": [],
        }
        # Even if not targeted, speech is publicly observable
        visible = filter_visible_actions([action], "角色B")
        assert len(visible) == 1
        assert visible[0]["inner_reasoning"] == ""

    def test_multiple_actions_filter(
        self,
        sample_action_robert: ActionPack,
        sample_action_ned: ActionPack,
    ):
        all_actions = [sample_action_robert, sample_action_ned]

        # Robert sees Ned's action (targeted at him)
        visible_to_robert = filter_visible_actions(all_actions, "劳勃国王")
        assert len(visible_to_robert) == 1
        assert visible_to_robert[0]["character_id"] == "艾德"

        # Ned sees Robert's action (targeted at him)
        visible_to_ned = filter_visible_actions(all_actions, "艾德")
        assert len(visible_to_ned) == 1
        assert visible_to_ned[0]["character_id"] == "劳勃国王"


class TestFilterKnownInfo:
    def test_includes_public_info(self):
        info: list[TaggedInfo] = [
            {"content": "公共信息", "visibility": "公开", "source": "test", "known_by": []},
        ]
        result = filter_known_info(info, "任何人")
        assert len(result) == 1

    def test_includes_own_private_info(self):
        info: list[TaggedInfo] = [
            {"content": "私有信息", "visibility": "私有", "source": "test", "known_by": ["角色A"]},
        ]
        result = filter_known_info(info, "角色A")
        assert len(result) == 1

    def test_excludes_others_private_info(self):
        info: list[TaggedInfo] = [
            {"content": "角色A的秘密", "visibility": "私有", "source": "test", "known_by": ["角色A"]},
        ]
        result = filter_known_info(info, "角色B")
        assert len(result) == 0

    def test_mixed_visibility(self):
        info: list[TaggedInfo] = [
            {"content": "公共", "visibility": "公开", "source": "test", "known_by": []},
            {"content": "A的秘密", "visibility": "私有", "source": "test", "known_by": ["A"]},
            {"content": "B的秘密", "visibility": "私有", "source": "test", "known_by": ["B"]},
        ]
        result = filter_known_info(info, "A")
        assert len(result) == 2  # public + A's private
