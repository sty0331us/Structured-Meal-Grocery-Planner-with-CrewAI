"""FastAPI application exposing the weekly planner."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from meal_planner.config import get_settings
from meal_planner.models import PlannerRequest, PlannerResult
from meal_planner.services import PlannerService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("Meal planner API starting in %s mode", settings.app_env)
    yield
    logger.info("Meal planner API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Structured Meal & Grocery Planner",
        description=(
            "Production multi-agent weekly meal and grocery planner powered by CrewAI "
            "with strict Pydantic structured outputs."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    service = PlannerService()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    @app.post("/v1/plans/weekly", response_model=PlannerResult)
    def create_weekly_plan(
        request: PlannerRequest,
        use_llm: bool = Query(
            default=True,
            description="Set false to run deterministic offline sample (CI / demos)",
        ),
    ) -> PlannerResult:
        try:
            return service.plan(request, use_llm=use_llm)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — surface crew failures cleanly
            logger.exception("Weekly plan generation failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


app = create_app()
