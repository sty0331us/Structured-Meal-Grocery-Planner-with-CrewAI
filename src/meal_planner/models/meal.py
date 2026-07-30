"""Core meal domain models."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MealType(str, Enum):
    """Supported meal categories for weekly planning."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class DietaryTag(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    HIGH_PROTEIN = "high_protein"
    LOW_CARB = "low_carb"
    HALAL = "halal"
    KOSHER = "kosher"


class Ingredient(BaseModel):
    """A single researched ingredient with quantity metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, description="Ingredient name")
    quantity: float = Field(..., gt=0, description="Numeric quantity")
    unit: str = Field(..., min_length=1, description="Unit of measure (g, ml, pcs, cups, etc.)")
    estimated_cost: Optional[float] = Field(
        default=None, ge=0, description="Estimated cost in plan currency"
    )
    optional: bool = Field(default=False, description="Whether the ingredient is optional")
    notes: Optional[str] = Field(default=None, description="Prep or substitution notes")


class MealPlan(BaseModel):
    """A single structured meal plan with researched ingredients."""

    model_config = ConfigDict(str_strip_whitespace=True)

    meal_name: str = Field(..., min_length=1, description="Name of the meal")
    meal_type: MealType = Field(default=MealType.DINNER, description="Meal category")
    difficulty_level: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM, description="Preparation difficulty"
    )
    servings: int = Field(default=2, ge=1, le=20, description="Number of servings")
    researched_ingredients: list[str] = Field(
        default_factory=list,
        description="Legacy flat ingredient names for compatibility",
    )
    ingredients: list[Ingredient] = Field(
        default_factory=list, description="Structured ingredient list"
    )
    estimated_cost: Optional[float] = Field(
        default=None, ge=0, description="Estimated total meal cost"
    )
    prep_time_minutes: Optional[int] = Field(default=None, ge=0, le=480)
    cook_time_minutes: Optional[int] = Field(default=None, ge=0, le=480)
    dietary_tags: list[DietaryTag] = Field(default_factory=list)
    cuisine: Optional[str] = Field(default=None, description="Cuisine style")
    instructions_summary: Optional[str] = Field(
        default=None, description="Short cooking overview"
    )
    leftover_friendly: bool = Field(
        default=False, description="Whether leftovers store well for later meals"
    )

    @field_validator("researched_ingredients")
    @classmethod
    def normalize_ingredient_names(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item and item.strip()]

    @property
    def all_ingredient_names(self) -> list[str]:
        names = list(self.researched_ingredients)
        names.extend(item.name.strip().lower() for item in self.ingredients)
        # preserve order, drop duplicates
        seen: set[str] = set()
        unique: list[str] = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique.append(name)
        return unique
