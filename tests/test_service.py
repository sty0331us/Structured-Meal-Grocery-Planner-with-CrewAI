"""Service and optimizer integration tests (offline, no LLM)."""

from __future__ import annotations

from meal_planner.models import PlannerRequest
from meal_planner.services import PlannerService
from meal_planner.services.optimizer import aggregate_ingredients, mark_bulk_items


def test_offline_planner_service(planner_request: PlannerRequest) -> None:
    service = PlannerService()
    result = service.plan(planner_request, use_llm=False)

    assert result.weekly_meal_plan.week_start_date == "2024-01-15"
    assert len(result.weekly_meal_plan.daily_meals) == 7
    assert result.weekly_meal_plan.total_meals == 21
    assert result.weekly_grocery_plan.weekly_budget_amount == 150.0
    assert result.weekly_grocery_plan.item_count > 0
    assert result.provenance["engine"] == "offline-sample"


def test_bulk_optimizer_flags_reused_staples(planner_request: PlannerRequest) -> None:
    service = PlannerService()
    plan = service.plan(planner_request, use_llm=False).weekly_meal_plan
    items = aggregate_ingredients(plan)
    bulk = mark_bulk_items(items, min_meal_uses=2, min_quantity=2.0)
    assert bulk
    assert all(item.is_bulk for item in bulk)
