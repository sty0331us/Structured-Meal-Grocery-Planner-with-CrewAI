"""CrewAI tools for budget + bulk shopping optimization."""

from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from meal_planner.models import WeeklyMealPlan
from meal_planner.services.optimizer import build_grocery_plan, mark_bulk_items, aggregate_ingredients


class BulkOptimizeInput(BaseModel):
    weekly_meal_plan_json: str = Field(
        ..., description="JSON string of a WeeklyMealPlan payload"
    )
    min_meal_uses: int = Field(default=3, ge=2, le=14)
    min_quantity: float = Field(default=3.0, gt=0)


class BulkOptimizeTool(BaseTool):
    name: str = "bulk_shopping_optimizer"
    description: str = (
        "Analyze a weekly meal plan and return grocery items that should be purchased "
        "in bulk because they are reused across many meals or needed in high quantity."
    )
    args_schema: Type[BaseModel] = BulkOptimizeInput

    def _run(
        self,
        weekly_meal_plan_json: str,
        min_meal_uses: int = 3,
        min_quantity: float = 3.0,
    ) -> str:
        plan = WeeklyMealPlan.model_validate(json.loads(weekly_meal_plan_json))
        items = aggregate_ingredients(plan)
        bulk = mark_bulk_items(items, min_meal_uses=min_meal_uses, min_quantity=min_quantity)
        return json.dumps([item.model_dump() for item in bulk], indent=2)


class GroceryBuildInput(BaseModel):
    weekly_meal_plan_json: str = Field(..., description="JSON string of WeeklyMealPlan")
    weekly_budget: float = Field(..., gt=0)
    currency: str = Field(default="USD")
    enable_bulk: bool = Field(default=True)


class GroceryBuildTool(BaseTool):
    name: str = "weekly_grocery_builder"
    description: str = (
        "Build a structured WeeklyGroceryPlan from a WeeklyMealPlan: aggregate "
        "ingredients, group by store section, mark bulk items, and allocate daily budget."
    )
    args_schema: Type[BaseModel] = GroceryBuildInput

    def _run(
        self,
        weekly_meal_plan_json: str,
        weekly_budget: float,
        currency: str = "USD",
        enable_bulk: bool = True,
    ) -> str:
        plan = WeeklyMealPlan.model_validate(json.loads(weekly_meal_plan_json))
        grocery = build_grocery_plan(
            plan,
            weekly_budget=weekly_budget,
            currency=currency,
            enable_bulk=enable_bulk,
        )
        return grocery.model_dump_json(indent=2)


class BudgetCheckInput(BaseModel):
    estimated_total: float = Field(..., ge=0)
    weekly_budget: float = Field(..., gt=0)


class BudgetCheckTool(BaseTool):
    name: str = "budget_compliance_check"
    description: str = (
        "Compare estimated grocery total against the weekly budget and return "
        "over/under status with recommended corrective actions."
    )
    args_schema: Type[BaseModel] = BudgetCheckInput

    def _run(self, estimated_total: float, weekly_budget: float) -> str:
        remaining = round(weekly_budget - estimated_total, 2)
        status = "under_budget" if remaining >= 0 else "over_budget"
        actions: list[str] = []
        if remaining < 0:
            actions = [
                "Swap one premium animal protein for beans, lentils, or tofu",
                "Reduce specialty snack line items",
                "Prefer store-brand pantry staples",
            ]
        elif remaining > weekly_budget * 0.2:
            actions = [
                "Add a higher-quality produce item or fresh herb set",
                "Include a batch-cook protein for next week's prep",
            ]
        else:
            actions = ["Budget is healthy — keep the current plan"]

        return json.dumps(
            {
                "status": status,
                "estimated_total": estimated_total,
                "weekly_budget": weekly_budget,
                "remaining": remaining,
                "actions": actions,
            },
            indent=2,
        )
