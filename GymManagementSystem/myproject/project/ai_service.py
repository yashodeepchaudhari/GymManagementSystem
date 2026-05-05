"""
Gemini-powered AI plan generator.

Wraps the google-generativeai SDK in a single function `generate_fitness_plan`
that takes a member's profile and returns a parsed JSON dict with both
workout (7-day split) and diet (per-day meals) plans.

Falls back to a deterministic mock plan if GEMINI_API_KEY is missing — useful
for local development without burning API quota.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a certified personal trainer and nutritionist.
Generate a personalized 7-day workout split AND a 7-day diet plan for the following member.

Member profile:
- Name: {name}
- Age: {age}
- Gender: {gender}
- Height: {height_cm} cm
- Weight: {weight_kg} kg
- BMI: {bmi}
- Goal: {goal}
- Experience level: {experience}
- Diet preference: {diet}

Respond with VALID JSON only, no markdown, matching exactly this schema:
{{
  "summary": "1-2 sentence overview of the approach",
  "workout": [
    {{ "day": "Monday", "focus": "Chest & Triceps", "exercises": [
      {{ "name": "Bench Press", "sets": 4, "reps": "8-10" }}
    ]}}
    // 7 days total: Monday..Sunday. Use "Rest" for rest days with empty exercises array.
  ],
  "diet": [
    {{ "day": "Monday", "meals": {{
      "breakfast": "...",
      "lunch": "...",
      "snack": "...",
      "dinner": "..."
    }}, "calories_approx": 2200 }}
    // 7 days total
  ],
  "tips": ["short actionable tip", "..."]
}}
"""


def _build_prompt(member) -> str:
    return PROMPT_TEMPLATE.format(
        name=member.name,
        age=member.age,
        gender=member.gender or 'unspecified',
        height_cm=member.height_cm or 'unknown',
        weight_kg=member.weight_kg or 'unknown',
        bmi=member.bmi or 'unknown',
        goal=member.goal or 'general fitness',
        experience=member.experience or 'beginner',
        diet=member.diet or 'no preference',
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Gemini sometimes wraps JSON in ```json fences. Strip and parse."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


def _mock_plan(member) -> dict[str, Any]:
    """Used when no API key is configured — lets the UI work end-to-end locally."""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    focus = ['Chest & Triceps', 'Back & Biceps', 'Legs', 'Rest', 'Shoulders & Core', 'Full Body', 'Rest']
    return {
        "summary": f"Mock plan for {member.name} (set GEMINI_API_KEY in .env for AI-generated plans).",
        "workout": [
            {
                "day": d,
                "focus": f,
                "exercises": [] if f == 'Rest' else [
                    {"name": "Compound lift", "sets": 4, "reps": "8-10"},
                    {"name": "Isolation 1", "sets": 3, "reps": "10-12"},
                    {"name": "Isolation 2", "sets": 3, "reps": "12-15"},
                ],
            }
            for d, f in zip(days, focus)
        ],
        "diet": [
            {
                "day": d,
                "meals": {
                    "breakfast": "Oats + banana + 3 egg whites",
                    "lunch": "Grilled chicken / paneer + brown rice + salad",
                    "snack": "Greek yogurt + nuts",
                    "dinner": "Fish / dal + roti + sabzi",
                },
                "calories_approx": 2200,
            }
            for d in days
        ],
        "tips": [
            "Hydrate: aim for 3L water/day.",
            "Sleep 7-8 hours for recovery.",
            "Progressive overload — add weight each week.",
        ],
    }


def generate_fitness_plan(member) -> tuple[dict[str, Any], str]:
    """
    Returns (parsed_dict, raw_text).
    raw_text is the model's full response (or pretty mock JSON), useful for storage/debug.
    """
    if not settings.GEMINI_API_KEY:
        plan = _mock_plan(member)
        return plan, json.dumps(plan, indent=2)

    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel('gemini-flash-latest')
    prompt = _build_prompt(member)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.7,
                'response_mime_type': 'application/json',
            },
        )
        raw = response.text or ''
        parsed = _extract_json(raw)
        return parsed, raw
    except json.JSONDecodeError as e:
        logger.warning("Gemini returned non-JSON: %s", e)
        return _mock_plan(member), getattr(response, 'text', '')
    except Exception as e:
        logger.exception("Gemini call failed: %s", e)
        plan = _mock_plan(member)
        return plan, f"[ERROR: {e}]\n\n" + json.dumps(plan, indent=2)
