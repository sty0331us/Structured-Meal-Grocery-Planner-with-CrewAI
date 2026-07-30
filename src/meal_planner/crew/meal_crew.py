"""CrewAI multi-agent assembly for weekly meal & grocery planning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task

from meal_planner.config import get_settings
from meal_planner.models import PlannerRequest, WeeklyGroceryPlan, WeeklyMealPlan
from meal_planner.tools import BudgetCheckTool, BulkOptimizeTool, GroceryBuildTool

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class MealPlannerCrew:
    """Production crew: research → weekly architecture → grocery strategy."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.agents_config = _load_yaml("agents.yaml")
        self.tasks_config = _load_yaml("tasks.yaml")
        self.bulk_tool = BulkOptimizeTool()
        self.grocery_tool = GroceryBuildTool()
        self.budget_tool = BudgetCheckTool()

    def meal_researcher(self) -> Agent:
        cfg = self.agents_config["meal_researcher"]
        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            verbose=self.settings.crew_verbose,
            allow_delegation=False,
        )

    def weekly_meal_architect(self) -> Agent:
        cfg = self.agents_config["weekly_meal_architect"]
        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            verbose=self.settings.crew_verbose,
            allow_delegation=False,
        )

    def grocery_strategist(self) -> Agent:
        cfg = self.agents_config["grocery_strategist"]
        return Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            tools=[self.bulk_tool, self.grocery_tool, self.budget_tool],
            verbose=self.settings.crew_verbose,
            allow_delegation=False,
        )

    def research_task(self, agent: Agent, inputs: dict[str, Any]) -> Task:
        cfg = self.tasks_config["research_weekly_meals"]
        return Task(
            description=cfg["description"].format(**inputs),
            expected_output=cfg["expected_output"],
            agent=agent,
        )

    def design_task(self, agent: Agent, inputs: dict[str, Any], context: list[Task]) -> Task:
        cfg = self.tasks_config["design_weekly_meal_plan"]
        return Task(
            description=cfg["description"].format(**inputs),
            expected_output=cfg["expected_output"],
            agent=agent,
            context=context,
            output_pydantic=WeeklyMealPlan,
        )

    def grocery_task(self, agent: Agent, inputs: dict[str, Any], context: list[Task]) -> Task:
        cfg = self.tasks_config["build_weekly_grocery_plan"]
        return Task(
            description=cfg["description"].format(**inputs),
            expected_output=cfg["expected_output"],
            agent=agent,
            context=context,
            output_pydantic=WeeklyGroceryPlan,
        )

    def crew(self) -> Crew:
        researcher = self.meal_researcher()
        architect = self.weekly_meal_architect()
        strategist = self.grocery_strategist()

        # Placeholder inputs — replaced at kickoff via Task recreation
        placeholder = {
            "week_start_date": "2024-01-15",
            "household_size": 2,
            "weekly_budget": 150.0,
            "currency": "USD",
            "dietary_constraints": "none",
            "cuisine_preferences": "none",
            "banned_ingredients": "none",
            "meals_per_day": "breakfast, lunch, dinner",
            "include_snacks": False,
            "prep_time_preference": "balanced",
            "enable_bulk_optimization": True,
        }

        research = self.research_task(researcher, placeholder)
        design = self.design_task(architect, placeholder, [research])
        grocery = self.grocery_task(strategist, placeholder, [design])

        return Crew(
            agents=[researcher, architect, strategist],
            tasks=[research, design, grocery],
            process=Process.sequential,
            verbose=self.settings.crew_verbose,
            memory=self.settings.crew_memory,
        )

    def _request_inputs(self, request: PlannerRequest) -> dict[str, Any]:
        return {
            "week_start_date": request.week_start_date,
            "household_size": request.household_size,
            "weekly_budget": request.weekly_budget,
            "currency": request.currency,
            "dietary_constraints": ", ".join(request.dietary_constraints) or "none",
            "cuisine_preferences": ", ".join(request.cuisine_preferences) or "none",
            "banned_ingredients": ", ".join(request.banned_ingredients) or "none",
            "meals_per_day": ", ".join(m.value for m in request.meals_per_day),
            "include_snacks": request.include_snacks,
            "prep_time_preference": request.prep_time_preference or "balanced",
            "enable_bulk_optimization": request.enable_bulk_optimization,
        }

    def build_crew_for_request(self, request: PlannerRequest) -> Crew:
        inputs = self._request_inputs(request)
        researcher = self.meal_researcher()
        architect = self.weekly_meal_architect()
        strategist = self.grocery_strategist()

        research = self.research_task(researcher, inputs)
        design = self.design_task(architect, inputs, [research])
        grocery = self.grocery_task(strategist, inputs, [design])

        return Crew(
            agents=[researcher, architect, strategist],
            tasks=[research, design, grocery],
            process=Process.sequential,
            verbose=self.settings.crew_verbose,
            memory=self.settings.crew_memory,
        )

    def kickoff(self, request: PlannerRequest) -> Any:
        crew = self.build_crew_for_request(request)
        result = crew.kickoff(inputs=self._request_inputs(request))
        # Prefer the meal-plan task pydantic output when available
        for task_output in getattr(result, "tasks_output", []) or []:
            pydantic_out = getattr(task_output, "pydantic", None)
            if isinstance(pydantic_out, WeeklyMealPlan):
                return pydantic_out
        return result
