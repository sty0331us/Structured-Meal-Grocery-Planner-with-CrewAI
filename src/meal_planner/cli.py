"""Typer CLI for local / CI usage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from meal_planner.models import MealType, PlannerRequest
from meal_planner.services import PlannerService

app = typer.Typer(
    name="meal-planner",
    help="Structured weekly meal & grocery planner (CrewAI)",
    add_completion=False,
)
console = Console()


@app.command("plan")
def plan_week(
    week_start: str = typer.Option(..., "--week-start", help="YYYY-MM-DD week start"),
    budget: float = typer.Option(150.0, "--budget", help="Weekly grocery budget"),
    household_size: int = typer.Option(2, "--household-size", min=1, max=20),
    currency: str = typer.Option("USD", "--currency"),
    diets: Optional[list[str]] = typer.Option(None, "--diet", help="Dietary constraint"),
    cuisines: Optional[list[str]] = typer.Option(None, "--cuisine"),
    offline: bool = typer.Option(
        False, "--offline", help="Skip LLM crew; use deterministic sample plan"
    ),
    output: Optional[Path] = typer.Option(None, "--output", help="Write JSON result path"),
) -> None:
    """Generate a weekly meal plan and optimized grocery strategy."""

    request = PlannerRequest(
        week_start_date=week_start,
        household_size=household_size,
        weekly_budget=budget,
        currency=currency,
        dietary_constraints=diets or [],
        cuisine_preferences=cuisines or [],
        meals_per_day=[MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER],
    )
    service = PlannerService()
    result = service.plan(request, use_llm=not offline)

    meals = result.weekly_meal_plan
    grocery = result.weekly_grocery_plan

    table = Table(title=f"Week of {meals.week_start_date}")
    table.add_column("Date")
    table.add_column("Breakfast")
    table.add_column("Lunch")
    table.add_column("Dinner")
    for day in meals.daily_meals:
        table.add_row(
            day.date,
            day.breakfast.meal_name if day.breakfast else "—",
            day.lunch.meal_name if day.lunch else "—",
            day.dinner.meal_name if day.dinner else "—",
        )
    console.print(table)
    console.print(
        f"[bold]Meals:[/bold] {meals.total_meals}  |  "
        f"[bold]Grocery est.:[/bold] {grocery.currency} {grocery.estimated_total:.2f} / "
        f"{grocery.weekly_budget_amount:.2f}  |  "
        f"[bold]Bulk items:[/bold] {len(grocery.bulk_items)}"
    )

    if output:
        output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"Wrote {output}")


@app.command("validate-models")
def validate_models() -> None:
    """Run the Exercise 2 sample WeeklyMealPlan payload through Pydantic."""

    from meal_planner.models import DailyMeals, MealPlan, WeeklyMealPlan

    sample = WeeklyMealPlan(
        week_start_date="2024-01-15",
        daily_meals=[
            DailyMeals(
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
        ],
        weekly_themes=["Italian Monday", "Taco Tuesday"],
        prep_suggestions=["Wash vegetables on Sunday", "Cook grains in bulk"],
    )
    console.print_json(json.dumps(sample.model_dump()))
    console.print("[green]WeeklyMealPlan validation OK[/green]")


if __name__ == "__main__":
    app()
