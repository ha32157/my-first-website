from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Goal = Literal["weight loss", "muscle gain", "general wellness", "flexibility"]
Intensity = Literal["low", "medium", "high"]


class UserInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=13, le=100)
    weight_kg: float = Field(gt=20, le=350)
    goal: Goal
    intensity: Intensity


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    feedback: str = Field(min_length=5, max_length=2000)


class PlanResponse(BaseModel):
    user_id: str
    name: str
    age: int
    weight_kg: float
    goal: str
    intensity: str
    workout_plan: str
    nutrition_tip: str
    updated: bool = False


class HealthResponse(BaseModel):
    status: str
    database: str
    ai_mode: str
