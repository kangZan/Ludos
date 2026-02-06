"""Interaction store — persist and query action logs."""

import json
from pathlib import Path

import structlog

from src.models.types import ActionPack

logger = structlog.get_logger(__name__)


class InteractionStore:
    """Stores and queries interaction logs.

    Provides persistence beyond graph state and methods for
    retrieving actions by character, round, or keyword.
    """

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        self._actions: list[ActionPack] = []
        self._storage_dir = Path(storage_dir) if storage_dir else None

        if self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)

    def add_action(self, action: ActionPack) -> None:
        """Add an action to the store."""
        self._actions.append(action)

    def add_actions(self, actions: list[ActionPack]) -> None:
        """Add multiple actions to the store."""
        self._actions.extend(actions)

    def get_all(self) -> list[ActionPack]:
        """Get all stored actions."""
        return list(self._actions)

    def get_by_character(self, character_id: str) -> list[ActionPack]:
        """Get all actions by a specific character."""
        return [a for a in self._actions if a["character_id"] == character_id]

    def get_by_round(self, round_number: int) -> list[ActionPack]:
        """Get all actions from a specific round."""
        return [a for a in self._actions if a["round"] == round_number]

    def search_by_keyword(self, keyword: str) -> list[ActionPack]:
        """Search actions for a keyword in spoken or action content."""
        results: list[ActionPack] = []
        for action in self._actions:
            text = (action.get("spoken_content") or "") + (action.get("action_content") or "")
            if keyword in text:
                results.append(action)
        return results

    def save_to_file(self, session_id: str) -> Path | None:
        """Persist actions to a JSON file."""
        if not self._storage_dir:
            return None

        filepath = self._storage_dir / f"session_{session_id}.json"
        data = [dict(a) for a in self._actions]

        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info("store.saved", path=str(filepath), count=len(data))
        return filepath

    def load_from_file(self, session_id: str) -> bool:
        """Load actions from a previously saved file."""
        if not self._storage_dir:
            return False

        filepath = self._storage_dir / f"session_{session_id}.json"
        if not filepath.exists():
            return False

        data = json.loads(filepath.read_text(encoding="utf-8"))
        self._actions = data
        logger.info("store.loaded", path=str(filepath), count=len(data))
        return True
