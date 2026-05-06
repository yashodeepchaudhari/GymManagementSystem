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


CHAT_SYSTEM_TEMPLATE = """You are FitBot, a friendly AI fitness coach for {name}.
Their profile:
- Age {age}, gender {gender}, BMI {bmi}, goal: {goal}
- Experience: {experience}, diet: {diet}
- Plan: {plan_name}, expires {expiry}

Answer concisely (1-3 short paragraphs). Stay focused on fitness, nutrition,
form, recovery, motivation. If asked something unrelated or medical, politely
redirect or suggest seeing a professional.
"""


def _build_chat_system(member) -> str:
    plan_name = member.plan.name if member.plan_id else 'no plan'
    return CHAT_SYSTEM_TEMPLATE.format(
        name=member.name,
        age=member.age,
        gender=member.gender or 'unspecified',
        bmi=member.bmi or 'unknown',
        goal=member.get_goal_display() or 'general fitness',
        experience=member.get_experience_display() or 'beginner',
        diet=member.get_diet_display() or 'no preference',
        plan_name=plan_name,
        expiry=member.expiry_date or 'unknown',
    )


VISION_PROMPT_TEMPLATE = """You are a fitness coach analysing a body photo for {name}.

Member context:
- Age {age}, gender {gender}, height {height_cm}cm, weight {weight_kg}kg, BMI {bmi}
- Goal: {goal}, experience: {experience}

Look at the photo and respond with EXACTLY 3 short sections (no markdown headers, plain text):

1. POSTURE & PROPORTIONS — 2 sentences on what you observe (shoulders, hips, alignment).
2. AREAS TO FOCUS — 2-3 bullet points (use • for bullets) on muscle groups or postural fixes.
3. ENCOURAGEMENT — 1 motivating sentence.

Be respectful, evidence-based, and avoid claiming exact body-fat percentages. If the
photo doesn't clearly show a person, say so politely instead of guessing.
"""


def analyze_body_photo(member, image_bytes: bytes, mime_type: str = 'image/jpeg') -> str:
    """Send photo + member context to Gemini Vision; return text analysis."""
    if not settings.GEMINI_API_KEY:
        return ("(Vision offline — set GEMINI_API_KEY to enable AI analysis.)\n\n"
                "Posture & proportions: Looks balanced overall.\n"
                "Areas to focus:\n• Core stability\n• Posterior chain\n• Mobility\n"
                "Encouragement: Keep showing up — consistency wins!")

    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel('gemini-flash-latest')
    prompt = VISION_PROMPT_TEMPLATE.format(
        name=member.name,
        age=member.age,
        gender=member.gender or 'unspecified',
        height_cm=member.height_cm or 'unknown',
        weight_kg=member.weight_kg or 'unknown',
        bmi=member.bmi or 'unknown',
        goal=member.get_goal_display() or 'general fitness',
        experience=member.get_experience_display() or 'beginner',
    )
    try:
        resp = model.generate_content(
            [prompt, {'mime_type': mime_type, 'data': image_bytes}],
            generation_config={'temperature': 0.4},
        )
        return (resp.text or '').strip() or "(Vision returned empty response.)"
    except Exception as e:
        logger.exception("Gemini vision failed: %s", e)
        return f"AI analysis failed: {e}"


def chat_reply(member, user_message: str, history: list[dict]) -> str:
    """Send a member message + recent history to Gemini, return assistant reply.

    history is a list of {'role': 'user'|'assistant', 'content': str} items in order.
    Falls back to a stub reply if no API key is configured.
    """
    if not settings.GEMINI_API_KEY:
        return ("(FitBot offline — set GEMINI_API_KEY to enable AI chat.) "
                "Quick tip: drink water, sleep well, and stay consistent!")

    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel(
        'gemini-flash-latest',
        system_instruction=_build_chat_system(member),
    )

    # Convert history to Gemini's format. Gemini uses 'user' and 'model'.
    gemini_history = []
    for msg in history:
        gemini_history.append({
            'role': 'user' if msg['role'] == 'user' else 'model',
            'parts': [msg['content']],
        })

    try:
        chat = model.start_chat(history=gemini_history)
        resp = chat.send_message(user_message, generation_config={'temperature': 0.7})
        return (resp.text or '').strip() or "Sorry, I couldn't generate a reply. Try rephrasing?"
    except Exception as e:
        logger.exception("Gemini chat failed: %s", e)
        return f"FitBot ran into an issue: {e}. Try again in a moment."


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
