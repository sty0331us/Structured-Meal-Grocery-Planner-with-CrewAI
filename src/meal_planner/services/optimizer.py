"""Deterministic planning utilities used by agent tools and the service layer."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from meal_planner.models.grocery import GroceryItem, ShoppingCategory, StoreSection
from meal_planner.models.meal import MealPlan, MealType
from meal_planner.models.weekly import DailyMeals, WeeklyGroceryPlan, WeeklyMealPlan


SECTION_KEYWORDS: dict[StoreSection, tuple[str, ...]] = {
    StoreSection.PRODUCE: (
        "lettuce",
        "tomato",
        "onion",
        "garlic",
        "berry",
        "berries",
        "spinach",
        "avocado",
        "apple",
        "banana",
        "pepper",
        "carrot",
        "cucumber",
        "lemon",
        "lime",
        "herb",
        "cilantro",
        "basil",
        "potato",
        "broccoli",
    ),
    StoreSection.DAIRY: ("milk", "cheese", "yogurt", "butter", "cream", "egg"),
    StoreSection.MEAT_SEAFOOD: (
        "chicken",
        "beef",
        "pork",
        "turkey",
        "salmon",
        "shrimp",
        "fish",
        "tofu",
    ),
    StoreSection.BAKERY: ("bread", "tortilla", "bagel", "bun", "pita"),
    StoreSection.PANTRY: (
        "oat",
        "pasta",
        "rice",
        "sauce",
        "oil",
        "bean",
        "lentil",
        "flour",
        "sugar",
        "salt",
        "vinegar",
        "broth",
        "canned",
        "quinoa",
        "dressing",
    ),
    StoreSection.FROZEN: ("frozen", "ice cream"),
    StoreSection.BEVERAGES: ("juice", "coffee", "tea", "soda", "water"),
    StoreSection.SPICES: ("spice", "paprika", "cumin", "chili", "peppercorn", "oregano"),
}

DEFAULT_UNIT_COST: dict[str, float] = {
    "oats": 0.35,
    "milk": 1.2,
    "berries": 3.5,
    "lettuce": 1.5,
    "tomatoes": 1.8,
    "dressing": 2.5,
    "pasta": 1.4,
    "sauce": 2.0,
    "cheese": 3.0,
}


def infer_section(ingredient_name: str) -> StoreSection:
    name = ingredient_name.lower()
    for section, keywords in SECTION_KEYWORDS.items():
        if any(keyword in name for keyword in keywords):
            return section
    return StoreSection.OTHER


def estimate_unit_cost(ingredient_name: str) -> float:
    name = ingredient_name.lower()
    for key, cost in DEFAULT_UNIT_COST.items():
        if key in name:
            return cost
    return 1.5


def aggregate_ingredients(meal_plan: WeeklyMealPlan) -> list[GroceryItem]:
    """Collapse duplicate ingredients across the week for shopping efficiency."""

    buckets: dict[str, GroceryItem] = {}

    for day_date, meal in meal_plan.iter_meals():
        meal_label = f"{day_date}:{meal.meal_name}"
        if meal.ingredients:
            for ingredient in meal.ingredients:
                key = f"{ingredient.name.strip().lower()}|{ingredient.unit}"
                if key not in buckets:
                    buckets[key] = GroceryItem(
                        name=ingredient.name,
                        quantity=ingredient.quantity,
                        unit=ingredient.unit,
                        estimated_cost=ingredient.estimated_cost
                        or estimate_unit_cost(ingredient.name) * ingredient.quantity,
                        section=infer_section(ingredient.name),
                        used_in_meals=[meal_label],
                    )
                else:
                    existing = buckets[key]
                    existing.quantity += ingredient.quantity
                    existing.estimated_cost = round(
                        existing.estimated_cost
                        + (
                            ingredient.estimated_cost
                            or estimate_unit_cost(ingredient.name) * ingredient.quantity
                        ),
                        2,
                    )
                    if meal_label not in existing.used_in_meals:
                        existing.used_in_meals.append(meal_label)
        else:
            for name in meal.all_ingredient_names:
                key = f"{name}|unit"
                if key not in buckets:
                    buckets[key] = GroceryItem(
                        name=name,
                        quantity=1.0,
                        unit="unit",
                        estimated_cost=estimate_unit_cost(name),
                        section=infer_section(name),
                        used_in_meals=[meal_label],
                    )
                else:
                    existing = buckets[key]
                    existing.quantity += 1.0
                    existing.estimated_cost = round(
                        existing.estimated_cost + estimate_unit_cost(name), 2
                    )
                    if meal_label not in existing.used_in_meals:
                        existing.used_in_meals.append(meal_label)

    return list(buckets.values())


def mark_bulk_items(
    items: Iterable[GroceryItem], *, min_meal_uses: int = 3, min_quantity: float = 3.0
) -> list[GroceryItem]:
    """Flag staples that appear across many meals or in high quantity."""

    bulk: list[GroceryItem] = []
    for item in items:
        if len(item.used_in_meals) >= min_meal_uses or item.quantity >= min_quantity:
            item.is_bulk = True
            bulk.append(item)
    return bulk


def group_by_section(items: list[GroceryItem]) -> list[ShoppingCategory]:
    grouped: dict[StoreSection, list[GroceryItem]] = defaultdict(list)
    for item in items:
        grouped[item.section].append(item)

    sections: list[ShoppingCategory] = []
    for section, section_items in sorted(grouped.items(), key=lambda pair: pair[0].value):
        category = ShoppingCategory(section=section, items=section_items)
        category.recompute_subtotal()
        sections.append(category)
    return sections


def distribute_daily_budget(weekly_budget: float, days: list[DailyMeals]) -> dict[str, str]:
    if not days:
        return {}
    per_day = round(weekly_budget / len(days), 2)
    breakdown = {day.date: f"${per_day:.2f}" for day in days}
    for day in days:
        day.daily_budget_allocation = per_day
    return breakdown


def build_grocery_plan(
    meal_plan: WeeklyMealPlan,
    weekly_budget: float,
    *,
    currency: str = "USD",
    enable_bulk: bool = True,
) -> WeeklyGroceryPlan:
    items = aggregate_ingredients(meal_plan)
    bulk_items = mark_bulk_items(items) if enable_bulk else []
    sections = group_by_section(items)
    estimated_total = round(sum(item.estimated_cost for item in items), 2)
    budget_breakdown = distribute_daily_budget(weekly_budget, meal_plan.daily_meals)

    tips = [
        "Shop pantry staples and bulk items first to lock in unit savings.",
        "Buy produce mid-week for fresher mid-to-late week meals.",
        "Cross-utilize proteins across dinner and next-day lunch.",
    ]
    if enable_bulk and bulk_items:
        tips.append(
            f"Purchase {len(bulk_items)} bulk staple(s): "
            + ", ".join(item.name for item in bulk_items[:5])
        )
    if estimated_total > weekly_budget:
        tips.append(
            "Estimated cart exceeds budget — substitute premium proteins or increase "
            "plant-based dinners."
        )

    return WeeklyGroceryPlan(
        weekly_budget=f"{currency} {weekly_budget:.2f}",
        weekly_budget_amount=weekly_budget,
        currency=currency,
        meal_plans=meal_plan.daily_meals,
        shopping_sections=sections,
        bulk_items=bulk_items,
        shopping_tips=tips,
        budget_breakdown=budget_breakdown,
        estimated_total=estimated_total,
    )


def ensure_meal_types(meals: list[MealPlan]) -> list[MealPlan]:
    for meal in meals:
        if meal.meal_type is None:
            meal.meal_type = MealType.DINNER
    return meals
