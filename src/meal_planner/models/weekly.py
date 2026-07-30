"""Weekly meal and grocery planning models (Exercise 2 extension)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from meal_planner.models.grocery import GroceryItem, ShoppingCategory
from meal_planner.models.meal import MealPlan, MealType


class DailyMeals(BaseModel):
    """All meals scheduled for a single calendar day."""

    model_config = ConfigDict(str_strip_whitespace=True)

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    breakfast: Optional[MealPlan] = Field(default=None, description="Breakfast meal plan")
    lunch: Optional[MealPlan] = Field(default=None, description="Lunch meal plan")
    dinner: Optional[MealPlan] = Field(default=None, description="Dinner meal plan")
    snacks: Optional[list[MealPlan]] = Field(default=None, description="Snack meal plans")
    daily_budget_allocation: Optional[float] = Field(
        default=None, ge=0, description="Optional per-day budget slice"
    )
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_iso_date(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("date must be ISO format YYYY-MM-DD") from exc
        return value

    @model_validator(mode="after")
    def assign_meal_types(self) -> DailyMeals:
        if self.breakfast is not None:
            self.breakfast.meal_type = MealType.BREAKFAST
        if self.lunch is not None:
            self.lunch.meal_type = MealType.LUNCH
        if self.dinner is not None:
            self.dinner.meal_type = MealType.DINNER
        if self.snacks:
            for snack in self.snacks:
                snack.meal_type = MealType.SNACK
        return self

    def all_meals(self) -> list[MealPlan]:
        meals: list[MealPlan] = []
        for meal in (self.breakfast, self.lunch, self.dinner):
            if meal is not None:
                meals.append(meal)
        if self.snacks:
            meals.extend(self.snacks)
        return meals

    @property
    def meal_count(self) -> int:
        return len(self.all_meals())


class WeeklyMealPlan(BaseModel):
    """Complete weekly meal planning across multiple days and meal types."""

    model_config = ConfigDict(str_strip_whitespace=True)

    week_start_date: str = Field(..., description="Start date of the week (YYYY-MM-DD)")
    daily_meals: list[DailyMeals] = Field(
        ..., min_length=1, max_length=7, description="Meals for each day"
    )
    weekly_themes: list[str] = Field(
        default_factory=list, description="Cooking themes for the week"
    )
    prep_suggestions: list[str] = Field(
        default_factory=list, description="Meal prep recommendations"
    )
    household_size: int = Field(default=2, ge=1, le=20)
    dietary_constraints: list[str] = Field(default_factory=list)
    total_estimated_meal_cost: Optional[float] = Field(default=None, ge=0)

    @field_validator("week_start_date")
    @classmethod
    def validate_week_start(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("week_start_date must be ISO format YYYY-MM-DD") from exc
        return value

    @model_validator(mode="after")
    def validate_week_span(self) -> WeeklyMealPlan:
        start = date.fromisoformat(self.week_start_date)
        end = start + timedelta(days=6)
        dates = [date.fromisoformat(day.date) for day in self.daily_meals]

        if len(dates) != len(set(dates)):
            raise ValueError("daily_meals must contain unique calendar dates")

        for day in dates:
            if day < start or day > end:
                raise ValueError(
                    f"daily meal date {day.isoformat()} falls outside week starting "
                    f"{self.week_start_date}"
                )
        return self

    def iter_meals(self) -> list[tuple[str, MealPlan]]:
        pairs: list[tuple[str, MealPlan]] = []
        for day in self.daily_meals:
            for meal in day.all_meals():
                pairs.append((day.date, meal))
        return pairs

    @property
    def total_meals(self) -> int:
        return sum(day.meal_count for day in self.daily_meals)

    def meals_by_type(self, meal_type: MealType) -> list[MealPlan]:
        return [meal for _, meal in self.iter_meals() if meal.meal_type == meal_type]


class BudgetBreakdown(BaseModel):
    """Named budget slices for reporting and agent hand-off."""

    model_config = ConfigDict(str_strip_whitespace=True)

    allocations: dict[str, float] = Field(
        default_factory=dict,
        description="Named allocations e.g. produce, protein, pantry, contingency",
    )
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("allocations")
    @classmethod
    def non_negative_allocations(cls, value: dict[str, float]) -> dict[str, float]:
        for key, amount in value.items():
            if amount < 0:
                raise ValueError(f"allocation '{key}' cannot be negative")
        return value

    @property
    def total(self) -> float:
        return round(sum(self.allocations.values()), 2)


class WeeklyGroceryPlan(BaseModel):
    """Weekly grocery shopping strategy with bulk optimization and budget control."""

    model_config = ConfigDict(str_strip_whitespace=True)

    weekly_budget: str = Field(..., description="Total weekly budget as formatted string")
    weekly_budget_amount: float = Field(..., gt=0, description="Numeric weekly budget")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    meal_plans: list[DailyMeals] = Field(..., description="All weekly meals")
    shopping_sections: list[ShoppingCategory] = Field(
        default_factory=list, description="Organized by store sections"
    )
    bulk_items: list[GroceryItem] = Field(
        default_factory=list, description="Items to buy in bulk"
    )
    shopping_tips: list[str] = Field(
        default_factory=list, description="Weekly shopping efficiency tips"
    )
    budget_breakdown: dict[str, str] = Field(
        default_factory=dict, description="Daily / category budget allocation labels"
    )
    structured_budget: Optional[BudgetBreakdown] = Field(
        default=None, description="Typed budget allocation when available"
    )
    estimated_total: float = Field(default=0.0, ge=0)
    remaining_budget: Optional[float] = None
    store_preference: Optional[str] = None

    @model_validator(mode="after")
    def sync_remaining_budget(self) -> WeeklyGroceryPlan:
        if self.remaining_budget is None:
            self.remaining_budget = round(self.weekly_budget_amount - self.estimated_total, 2)
        return self

    @property
    def is_over_budget(self) -> bool:
        return self.estimated_total > self.weekly_budget_amount

    @property
    def item_count(self) -> int:
        return sum(len(section.items) for section in self.shopping_sections)


class PlannerRequest(BaseModel):
    """API / CLI input for generating a weekly plan."""

    model_config = ConfigDict(str_strip_whitespace=True)

    week_start_date: str = Field(..., description="Monday (or preferred start) YYYY-MM-DD")
    household_size: int = Field(default=2, ge=1, le=20)
    weekly_budget: float = Field(default=150.0, gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    dietary_constraints: list[str] = Field(default_factory=list)
    cuisine_preferences: list[str] = Field(default_factory=list)
    banned_ingredients: list[str] = Field(default_factory=list)
    meals_per_day: list[MealType] = Field(
        default_factory=lambda: [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER]
    )
    include_snacks: bool = False
    prep_time_preference: Optional[str] = Field(
        default="balanced", description="quick | balanced | elaborate"
    )
    enable_bulk_optimization: bool = True

    @field_validator("week_start_date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("week_start_date must be ISO format YYYY-MM-DD") from exc
        return value


class PlannerResult(BaseModel):
    """Aggregated crew output returned to clients."""

    model_config = ConfigDict(str_strip_whitespace=True)

    request: PlannerRequest
    weekly_meal_plan: WeeklyMealPlan
    weekly_grocery_plan: WeeklyGroceryPlan
    provenance: dict[str, str] = Field(
        default_factory=dict,
        description="Agent / version metadata for auditability",
    )
