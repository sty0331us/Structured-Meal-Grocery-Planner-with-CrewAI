"""Exercise 2 — Pydantic weekly planning model tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from meal_planner.models import DailyMeals, MealPlan, MealType, WeeklyMealPlan
from meal_planner.services.optimizer import build_grocery_plan


def test_meal_type_enum_values() -> None:
    assert MealType.BREAKFAST.value == "breakfast"
    assert MealType.LUNCH.value == "lunch"
    assert MealType.DINNER.value == "dinner"
    assert MealType.SNACK.value == "snack"


def test_daily_meals_assigns_meal_types(sample_daily_meals: DailyMeals) -> None:
    assert sample_daily_meals.breakfast is not None
    assert sample_daily_meals.breakfast.meal_type == MealType.BREAKFAST
    assert sample_daily_meals.lunch is not None
    assert sample_daily_meals.lunch.meal_type == MealType.LUNCH
    assert sample_daily_meals.dinner is not None
    assert sample_daily_meals.dinner.meal_type == MealType.DINNER
    assert sample_daily_meals.meal_count == 3


def test_weekly_meal_plan_exercise_sample(sample_weekly_plan: WeeklyMealPlan) -> None:
    payload = sample_weekly_plan.model_dump()
    assert payload["week_start_date"] == "2024-01-15"
    assert len(payload["daily_meals"]) == 1
    assert payload["weekly_themes"] == ["Italian Monday", "Taco Tuesday"]
    assert "Wash vegetables on Sunday" in payload["prep_suggestions"]
    assert sample_weekly_plan.total_meals == 3


def test_weekly_meal_plan_rejects_out_of_range_dates(sample_daily_meals: DailyMeals) -> None:
    sample_daily_meals.date = "2024-02-01"
    with pytest.raises(ValidationError):
        WeeklyMealPlan(
            week_start_date="2024-01-15",
            daily_meals=[sample_daily_meals],
            weekly_themes=[],
            prep_suggestions=[],
        )


def test_weekly_meal_plan_rejects_duplicate_dates(sample_daily_meals: DailyMeals) -> None:
    with pytest.raises(ValidationError):
        WeeklyMealPlan(
            week_start_date="2024-01-15",
            daily_meals=[sample_daily_meals, sample_daily_meals.model_copy()],
            weekly_themes=[],
            prep_suggestions=[],
        )


def test_full_week_of_meals() -> None:
    from datetime import date, timedelta

    start = date(2024, 1, 15)
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        days.append(
            DailyMeals(
                date=day.isoformat(),
                breakfast=MealPlan(
                    meal_name=f"Breakfast {offset}",
                    difficulty_level="Easy",
                    servings=2,
                    researched_ingredients=["oats", "milk"],
                ),
                lunch=MealPlan(
                    meal_name=f"Lunch {offset}",
                    difficulty_level="Easy",
                    servings=2,
                    researched_ingredients=["lettuce", "tomatoes"],
                ),
                dinner=MealPlan(
                    meal_name=f"Dinner {offset}",
                    difficulty_level="Medium",
                    servings=2,
                    researched_ingredients=["pasta", "sauce", "cheese"],
                ),
                snacks=[
                    MealPlan(
                        meal_name=f"Snack {offset}",
                        difficulty_level="Easy",
                        servings=1,
                        researched_ingredients=["yogurt"],
                    )
                ],
            )
        )

    plan = WeeklyMealPlan(
        week_start_date="2024-01-15",
        daily_meals=days,
        weekly_themes=["Prep Week"],
        prep_suggestions=["Batch cook grains"],
    )
    assert plan.total_meals == 28
    assert len(plan.meals_by_type(MealType.SNACK)) == 7


def test_weekly_grocery_plan_from_meals(sample_weekly_plan: WeeklyMealPlan) -> None:
    grocery = build_grocery_plan(sample_weekly_plan, weekly_budget=100.0)
    assert grocery.weekly_budget_amount == 100.0
    assert grocery.item_count > 0
    assert "2024-01-15" in grocery.budget_breakdown
    assert grocery.shopping_sections
    assert grocery.shopping_tips
