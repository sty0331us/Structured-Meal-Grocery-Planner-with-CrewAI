"""Shared fixtures for model and service tests."""

from __future__ import annotations

import pytest

from meal_planner.models import DailyMeals, MealPlan, PlannerRequest, WeeklyMealPlan


@pytest.fixture
def sample_daily_meals() -> DailyMeals:
    return DailyMeals(
        date="2024-01-15",
        breakfast=MealPlan(
            meal_name="Oatmeal",
            difficulty_level="Easy",
            servings=2,
            researched_ingredients=["oats", "milk", "berries"],
        ),
        lunch=MealPlan(
            meal_name="Salad",
            difficulty_level="Easy",
            servings=2,
            researched_ingredients=["lettuce", "tomatoes", "dressing"],
        ),
        dinner=MealPlan(
            meal_name="Pasta",
            difficulty_level="Medium",
            servings=2,
            researched_ingredients=["pasta", "sauce", "cheese"],
        ),
    )


@pytest.fixture
def sample_weekly_plan(sample_daily_meals: DailyMeals) -> WeeklyMealPlan:
    return WeeklyMealPlan(
        week_start_date="2024-01-15",
        daily_meals=[sample_daily_meals],
        weekly_themes=["Italian Monday", "Taco Tuesday"],
        prep_suggestions=["Wash vegetables on Sunday", "Cook grains in bulk"],
    )


@pytest.fixture
def planner_request() -> PlannerRequest:
    return PlannerRequest(
        week_start_date="2024-01-15",
        household_size=2,
        weekly_budget=150.0,
        dietary_constraints=["vegetarian"],
        cuisine_preferences=["Italian", "Mexican"],
    )
