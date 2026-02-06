"""Tool modules for the deduction system."""

from src.tools.end_detector import check_end_conditions
from src.tools.info_filter import filter_known_info, filter_visible_actions
from src.tools.pressure_tracker import calculate_pressure_deltas, check_pressure_warnings
from src.tools.registry import load_tool_plugins, register_tool
from src.tools.turn_manager import determine_turn_order


def register_builtin_tools() -> None:
    """Register built-in tools and load plugins."""
    register_tool("filter_visible_actions", filter_visible_actions)
    register_tool("filter_known_info", filter_known_info)
    register_tool("calculate_pressure_deltas", calculate_pressure_deltas)
    register_tool("check_pressure_warnings", check_pressure_warnings)
    register_tool("determine_turn_order", determine_turn_order)
    register_tool("check_end_conditions", check_end_conditions)
    load_tool_plugins()


__all__ = [
    "register_builtin_tools",
]
