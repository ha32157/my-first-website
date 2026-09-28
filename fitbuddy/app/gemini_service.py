from __future__ import annotations

import json
import re
from typing import Any

from .config import Settings, get_settings
from .schemas import UserInput

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None


SYSTEM_INSTRUCTION = """
You are FitBuddy, a careful fitness-planning assistant. Create practical general-wellness
workout guidance from the user's provided profile. Do not diagnose medical conditions,
prescribe treatment, or claim that a workout is medically safe for a specific person.
Use conservative progression, include rest/recovery, and advise professional guidance when
there are injuries, medical restrictions, severe pain, dizziness, chest pain, or unusual
shortness of breath. Avoid extreme dieting and unsafe rapid weight-loss recommendations.
""".strip()


def _demo_plan(user: UserInput) -> str:
    focus = {
        "weight loss": "full-body strength + moderate cardio",
        "muscle gain": "strength and hypertrophy",
        "general wellness": "balanced full-body fitness",
        "flexibility": "mobility, flexibility, and light strength",
    }[user.goal]
    intensity_note = {
        "low": "Keep effort comfortable and leave several repetitions in reserve.",
        "medium": "Use a challenging but controlled effort and stop before form breaks down.",
        "high": "Use demanding but technically controlled sets; prioritize recovery between hard days.",
    }[user.intensity]
    days = [
        ("Day 1", "Full body", "Squat 3x8-12; Push-up 3x8-12; Row 3x8-12; Plank 3x30-45 sec"),
        ("Day 2", "Cardio + mobility", "Brisk walk/cycle 25-35 min; hip and shoulder mobility 10 min"),
        ("Day 3", "Upper body", "Press 3x8-12; Row 3x8-12; Lateral raise 2x12-15; Dead bug 3x8/side"),
        ("Day 4", "Recovery", "Easy walk 20-30 min; gentle stretching 10-15 min"),
        ("Day 5", "Lower body", "Squat or leg press 3x8-12; Hinge 3x8-12; Split squat 2x8/side; Calf raise 3x12-15"),
        ("Day 6", "Goal-focused conditioning", "Intervals or steady cardio 20-30 min; core circuit 2-3 rounds"),
        ("Day 7", "Rest", "Rest, easy walking if desired, hydration, and sleep-focused recovery"),
    ]
    lines = [f"7-DAY FITBUDDY PLAN — {user.name}", f"Goal: {user.goal} | Intensity: {user.intensity}", f"Focus: {focus}", "", f"Warm-up each training day: 5–10 minutes easy movement + dynamic mobility.", f"{intensity_note}", ""]
    for day, title, exercises in days:
        lines.extend([day + f" — {title}", f"  Main: {exercises}", "  Cooldown: 5–10 minutes easy movement and comfortable stretching.", ""])
    lines.append("Progression: when all prescribed reps feel controlled, increase resistance slightly or add 1–2 repetitions next week. Keep at least one full recovery day.")
    return "\n".join(lines)


def _demo_tip(goal: str) -> str:
    tips = {
        "weight loss": "Build meals around vegetables, a protein source, high-fiber carbohydrates, and water; aim for gradual, sustainable changes rather than aggressive restriction.",
        "muscle gain": "Include a protein-rich food at each meal and pair regular resistance training with adequate total food, sleep, and recovery.",
        "general wellness": "Keep hydration, regular meals, varied whole foods, sleep, and consistent activity as the foundation before optimizing details.",
        "flexibility": "Stay hydrated and include protein-rich foods and colorful fruits and vegetables while giving mobility work time to progress gradually.",
    }
    return tips[goal]


class GeminiService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = None
        if self.settings.gemini_api_key and genai is not None:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)

    @property
    def demo_mode(self) -> bool:
        return self.client is None

    def _generate(self, *, model: str, prompt: str, max_output_tokens: int | None = None) -> str:
        if self.client is None:
            raise RuntimeError("Gemini client is not configured")
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=self.settings.gemini_temperature,
            max_output_tokens=max_output_tokens or self.settings.gemini_max_output_tokens,
        )
        response = self.client.models.generate_content(model=model, contents=prompt, config=config)
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text.strip()

    def generate_workout(self, user: UserInput) -> str:
        if self.demo_mode:
            return _demo_plan(user)
        prompt = f"""
Create a structured 7-day fitness plan for:
Name: {user.name}
Age: {user.age}
Weight: {user.weight_kg} kg
Goal: {user.goal}
Preferred intensity: {user.intensity}

Requirements:
- Exactly seven labeled days.
- Include 5–10 minute warm-up on training days.
- Include exercises with sets/reps or duration and practical rest intervals.
- Include cooldown/recovery guidance.
- Include at least one recovery/rest day.
- Match exercise volume to the selected intensity.
- Do not provide medical diagnosis or unsafe extreme recommendations.
- Return plain text with clear headings; do not use markdown tables.
""".strip()
        return self._generate(model=self.settings.gemini_workout_model, prompt=prompt)

    def generate_tip(self, goal: str) -> str:
        if self.demo_mode:
            return _demo_tip(goal)
        prompt = f"Give one concise, practical nutrition or recovery tip for the fitness goal '{goal}'. Keep it under 80 words. Avoid medical claims and extreme dieting advice."
        return self._generate(model=self.settings.gemini_tip_model, prompt=prompt, max_output_tokens=500)

    def update_workout(self, user: UserInput, original_plan: str, feedback: str) -> str:
        if self.demo_mode:
            base = original_plan
            return base + f"\n\nUPDATED FROM USER FEEDBACK\nFeedback: {feedback}\nAdjustment: Keep the existing structure while applying this preference conservatively."
        prompt = f"""
Revise the following existing 7-day plan using the user's feedback.

USER PROFILE
Name: {user.name}
Age: {user.age}
Weight: {user.weight_kg} kg
Goal: {user.goal}
Intensity: {user.intensity}

ORIGINAL PLAN
{original_plan}

USER FEEDBACK
{feedback}

Return a complete revised seven-day plan, not a change log. Preserve useful parts of the original plan while applying reasonable feedback. Keep warm-up, workout details, cooldown/recovery, and at least one rest day. Avoid medical claims and unsafe recommendations.
""".strip()
        return self._generate(model=self.settings.gemini_workout_model, prompt=prompt)
