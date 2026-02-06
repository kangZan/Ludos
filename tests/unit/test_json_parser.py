"""Tests for the JSON parser utility."""

from src.utils.json_parser import extract_json


class TestExtractJson:
    def test_direct_json(self):
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_json_in_plain_code_block(self):
        text = '```\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"key": "value"}\nDone.'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_nested_json(self):
        text = '{"outer": {"inner": "value"}}'
        result = extract_json(text)
        assert result == {"outer": {"inner": "value"}}

    def test_array_json(self):
        text = '[1, 2, 3]'
        result = extract_json(text)
        assert result == [1, 2, 3]

    def test_trailing_comma(self):
        text = '{"key": "value",}'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_chinese_punctuation_fix(self):
        # Chinese comma and colon
        text = '{"key"\uff1a "value"\uff0c "key2": "v2"}'
        result = extract_json(text)
        assert result is not None
        assert result["key"] == "value"

    def test_no_json(self):
        result = extract_json("This is just plain text.")
        assert result is None

    def test_empty_string(self):
        result = extract_json("")
        assert result is None

    def test_complex_nested(self):
        text = """
        ```json
        {
          "purely_objective_facts": {
            "时空状态": "夜晚",
            "物理状态": "室内"
          },
          "character_dossiers": [
            {"角色标识": "测试角色"}
          ]
        }
        ```
        """
        result = extract_json(text)
        assert result is not None
        assert "purely_objective_facts" in result
        assert len(result["character_dossiers"]) == 1
