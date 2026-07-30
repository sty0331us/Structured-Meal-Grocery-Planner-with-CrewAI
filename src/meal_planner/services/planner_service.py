"""Planning service: orchestrates validation, crew execution, and post-processing."""

from __future__ import annotations

import json
import logging
from typing import Any

from meal_planner.config import get_settings
from meal_planner.crew.meal_crew import MealPlannerCrew
from meal_planner.models import PlannerRequest, PlannerResult, WeeklyGroceryPlan, WeeklyMealPlan
from meal_planner.services.optimizer import build_grocery_plan

logger = logging.getLogger(__name__)


class PlannerService:
    """High-level façade used by the CLI and HTTP API."""

    def __init__(self, crew: MealPlannerCrew | None = None) -> None:
        self.settings = get_settings()
        self.crew = crew or MealPlannerCrew()

    def plan(self, request: PlannerRequest, *, use_llm: bool = True) -> PlannerResult:
        if use_llm:
            raw = self.crew.kickoff(request)
            meal_plan = self._coerce_meal_plan(raw, request)
        else:
            meal_plan = self._offline_sample_plan(request)

        grocery_plan = build_grocery_plan(
            meal_plan,
            weekly_budget=request.weekly_budget,
            currency=request.currency,
            enable_bulk=request.enable_bulk_optimization
            and self.settings.enable_bulk_optimization,
        )

        return PlannerResult(
            request=request,
            weekly_meal_plan=meal_plan,
            weekly_grocery_plan=grocery_plan,
            provenance={
                "engine": "crewai" if use_llm else "offline-sample",
                "model": self.settings.llm_model if use_llm else "n/a",
                "version": "1.0.0",
            },
        )

    def _coerce_meal_plan(self, raw: Any, request: PlannerRequest) -> WeeklyMealPlan:
        if isinstance(raw, WeeklyMealPlan):
            return raw
        if hasattr(raw, "pydantic") and isinstance(raw.pydantic, WeeklyMealPlan):
            return raw.pydantic
        if hasattr(raw, "json_dict"):
            return WeeklyMealPlan.model_validate(raw.json_dict)
        if isinstance(raw, dict):
            return WeeklyMealPlan.model_validate(raw)
        if isinstance(raw, str):
            return WeeklyMealPlan.model_validate(json.loads(raw))
        if hasattr(raw, "raw"):
            payload = raw.raw
            if isinstance(payload, str):
                try:
                    return WeeklyMealPlan.model_validate(json.loads(payload))
                except json.JSONDecodeError:
                    logger.warning("Crew returned non-JSON raw output; using offline plan")
                    return self._offline_sample_plan(request)
            if isinstance(payload, dict):
                return WeeklyMealPlan.model_validate(payload)
        logger.warning("Unrecognized crew output type %s; using offline plan", type(raw))
        return self._offline_sample_plan(request)

    @staticmethod
    def _offline_sample_plan(request: PlannerRequest) -> WeeklyMealPlan:
        """Deterministic fallback for tests and demos without an API key."""

        from datetime import date, timedelta

        from meal_planner.models import DailyMeals, MealPlan

        start = date.fromisoformat(request.week_start_date)
        templates = [
            ("Overnight Oats", "Easy", ["oats", "milk", "berries"], "breakfast"),
            ("Chicken Salad Wrap", "Easy", ["chicken", "lettuce", "tortilla"], "lunch"),
            ("Tomato Basil Pasta", "Medium", ["pasta", "tomatoes", "basil", "cheese"], "dinner"),
            ("Veggie Stir Fry", "Easy", ["broccoli", "rice", "tofu", "soy sauce"], "dinner"),
            ("Taco Bowl", "Medium", ["beef", "rice", "beans", "avocado"], "dinner"),
            ("Greek Yogurt Bowl", "Easy", ["yogurt", "berries", "oats"], "breakfast"),
            ("Lentil Soup", "Easy", ["lentils", "carrot", "onion", "broth"], "lunch"),
        ]

        daily: list[DailyMeals] = []
        for offset in range(7):
            day = start + timedelta(days=offset)
            breakfast = templates[offset % len(templates)]
            lunch = templates[(offset + 1) % len(templates)]
            dinner = templates[(offset + 2) % len(templates)]
            daily.append(
                DailyMeals(
                    date=day.isoformat(),
                    breakfast=MealPlan(
                        meal_name=breakfast[0],
                        difficulty_level=breakfast[1],  # type: ignore[arg-type]
                        servings=request.household_size,
                        researched_ingredients=breakfast[2],
                    ),
                    lunch=MealPlan(
                        meal_name=lunch[0],
                        difficulty_level=lunch[1],  # type: ignore[arg-type]
                        servings=request.household_size,
                        researched_ingredients=lunch[2],
                    ),
                    dinner=MealPlan(
                        meal_name=dinner[0],
                        difficulty_level=dinner[1],  # type: ignore[arg-type]
                        servings=request.household_size,
                        researched_ingredients=dinner[2],
                    ),
                )
            )

        return WeeklyMealPlan(
            week_start_date=request.week_start_date,
            daily_meals=daily,
            weekly_themes=request.cuisine_preferences or ["Balanced Week", "Prep-Friendly"],
            prep_suggestions=[
                "Wash and chop vegetables on Sunday evening",
                "Cook grains in bulk for lunches",
                "Portion proteins for mid-week dinners",
            ],
            household_size=request.household_size,
            dietary_constraints=request.dietary_constraints,
        )


def merge_agent_grocery(
    meal_plan: WeeklyMealPlan,
    grocery: WeeklyGroceryPlan | dict[str, Any],
    request: PlannerRequest,
) -> WeeklyGroceryPlan:
    """Prefer structured optimizer output; overlay agent tips when present."""

    base = build_grocery_plan(
        meal_plan,
        weekly_budget=request.weekly_budget,
        currency=request.currency,
        enable_bulk=request.enable_bulk_optimization,
    )
    if isinstance(grocery, WeeklyGroceryPlan):
        if grocery.shopping_tips:
            base.shopping_tips = list(dict.fromkeys(base.shopping_tips + grocery.shopping_tips))
        if grocery.bulk_items:
            base.bulk_items = grocery.bulk_items
        return base
    tips = grocery.get("shopping_tips") if isinstance(grocery, dict) else None
    if isinstance(tips, list):
        base.shopping_tips = list(dict.fromkeys(base.shopping_tips + [str(t) for t in tips]))
    return base
