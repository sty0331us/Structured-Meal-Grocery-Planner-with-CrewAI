"""API smoke tests with FastAPI TestClient."""

from __future__ import annotations

from fastapi.testclient import TestClient

from meal_planner.api.app import create_app


client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_weekly_plan_offline() -> None:
    payload = {
        "week_start_date": "2024-01-15",
        "household_size": 2,
        "weekly_budget": 120.0,
        "dietary_constraints": ["vegetarian"],
        "cuisine_preferences": ["Italian"],
    }
    response = client.post("/v1/plans/weekly?use_llm=false", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["weekly_meal_plan"]["week_start_date"] == "2024-01-15"
    assert len(body["weekly_meal_plan"]["daily_meals"]) == 7
    assert body["weekly_grocery_plan"]["weekly_budget_amount"] == 120.0
