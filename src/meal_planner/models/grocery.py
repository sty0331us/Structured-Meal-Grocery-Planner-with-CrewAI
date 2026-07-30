"""Grocery domain models for weekly shopping optimization."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoreSection(str, Enum):
    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT_SEAFOOD = "meat_seafood"
    BAKERY = "bakery"
    PANTRY = "pantry"
    FROZEN = "frozen"
    BEVERAGES = "beverages"
    SPICES = "spices"
    OTHER = "other"


class GroceryItem(BaseModel):
    """A single grocery line item with aggregation metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1)
    estimated_cost: float = Field(default=0.0, ge=0)
    section: StoreSection = Field(default=StoreSection.OTHER)
    used_in_meals: list[str] = Field(
        default_factory=list, description="Meals that consume this item"
    )
    is_bulk: bool = Field(default=False, description="Recommended for bulk purchase")
    brand_preference: Optional[str] = None
    substitution: Optional[str] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower()


class ShoppingCategory(BaseModel):
    """Store-section grouping for efficient aisle navigation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    section: StoreSection
    items: list[GroceryItem] = Field(default_factory=list)
    section_subtotal: float = Field(default=0.0, ge=0)

    def recompute_subtotal(self) -> None:
        self.section_subtotal = round(sum(item.estimated_cost for item in self.items), 2)
