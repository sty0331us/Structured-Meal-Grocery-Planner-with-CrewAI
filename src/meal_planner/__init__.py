"""Package entrypoints."""

from meal_planner.api.app import app, create_app
from meal_planner.cli import app as cli

__all__ = ["app", "create_app", "cli"]
