"""Run the FastAPI server: python -m meal_planner.main"""

import uvicorn

from meal_planner.config import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "meal_planner.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=not settings.is_production,
    )


if __name__ == "__main__":
    run()
