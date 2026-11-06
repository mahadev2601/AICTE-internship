"""
agent/prompts.py — All LLM prompt templates for Fitness Buddy.

Each function returns a (system_prompt, user_message) tuple for IBM Granite chat API.

Output format: every prompt instructs the model to respond in clean Markdown
so the web UI can render it beautifully and it can be exported to PDF.

Anti-hallucination principles:
  1. Full user profile is embedded in every prompt — model personalises to REAL data.
  2. Static curated data (exercises, meals, quotes) is always passed in as context.
  3. Hard constraints forbid fabricated calorie counts, medical diagnoses, supplements.
  4. Low temperature (0.3) in config keeps outputs factual and consistent.
"""

from __future__ import annotations

# ── Shared system persona ─────────────────────────────────────────────────────
SYSTEM = (
    "You are Fitness Buddy, a professional AI health and fitness coach powered by IBM Granite. "
    "You give specific, actionable, evidence-based advice tailored to each user's exact profile. "
    "Always respond in clean Markdown with clear headings (##), bullet points (- ), and bold (**) for key terms. "
    "Be professional yet warm and encouraging. Use emojis sparingly for section headers only. "
    "NEVER invent calorie counts, exact macro grams, medical diagnoses, or supplement doses. "
    "NEVER fabricate quotes or attribute words to real people. "
    "If a question involves injury or medical conditions, always advise consulting a qualified doctor or physiotherapist. "
    "If a question is outside fitness or nutrition scope, politely decline."
)


def _profile_context(p: "UserProfile") -> str:  # type: ignore[name-defined]  # noqa: F821
    """Build a rich profile context string from the full UserProfile."""
    return (
        f"**User Profile:**\n"
        f"- Name: {p.name} | Age: {p.age} | Gender: {p.gender}\n"
        f"- Height/Weight: {p.height} / {p.weight}\n"
        f"- Goal: {p.goal.replace('_', ' ').title()} | Level: {p.level.title()}\n"
        f"- Schedule: {p.days_per_week} days/week, {p.time_per_session} min/session\n"
        f"- Equipment: {p.equipment or 'none — bodyweight only'}\n"
        f"- Diet: {p.dietary_pref or 'no preference'}\n"
        f"- Health notes: {p.health_notes or 'none'}\n"
        f"- Sleep: {p.sleep_hours} hrs/night | Stress: {p.stress_level}/10\n"
        f"- Motivation style: {p.motivation_style}"
    )


# ── Feature prompts ───────────────────────────────────────────────────────────

def workout_plan(p: "UserProfile", plan_key: str, routine: list[str]) -> tuple[str, str]:  # type: ignore[name-defined]  # noqa: F821
    """
    Generate a detailed, professionally structured workout plan in Markdown.
    The routine list is provided as a grounding anchor — the model expands each
    exercise with exact technique, sets, reps, and rest, but cannot invent new ones.
    """
    routine_text = "\n".join(f"  - {step}" for step in routine)
    user = (
        f"{_profile_context(p)}\n\n"
        f"Base workout plan ({plan_key.replace('_', ' ').title()}) to expand:\n{routine_text}\n\n"
        f"Generate a **detailed, professional workout plan** in Markdown for {p.name}. "
        f"Follow this exact structure:\n\n"
        f"## 💪 Your {plan_key.replace('_', ' ').title()} Workout Plan\n"
        f"Write a 2-sentence personalised intro referencing {p.name}'s goal and {p.time_per_session}-min schedule.\n\n"
        f"## 📋 Plan Overview\n"
        f"Table or bullets: Duration, Frequency, Equipment, Goal.\n\n"
        f"## 🔥 Warm-Up (5 min)\n"
        f"List 3 specific warm-up moves with duration each.\n\n"
        f"## 🏋️ Main Workout\n"
        f"For EACH exercise from the base routine, provide:\n"
        f"- **Exercise Name**: exact name\n"
        f"- **Sets × Reps**: specific numbers\n"
        f"- **Rest**: rest period\n"
        f"- **How to do it**: 1-sentence technique tip\n"
        f"- **Modification**: 1 easier option for beginners or if {p.name} has '{p.health_notes or 'no'} issues'\n\n"
        f"## 🧊 Cool-Down (5 min)\n"
        f"List 3 specific stretches with hold duration.\n\n"
        f"## 💡 Pro Tips for {p.name}\n"
        f"2 specific tips for {p.goal.replace('_', ' ')} based on their {p.level} level and {p.motivation_style} motivation style.\n\n"
        f"Constraints: Only use equipment available ({p.equipment or 'bodyweight'}). "
        f"Do NOT add exercises beyond the base routine. Do NOT invent calorie burns."
    )
    return SYSTEM, user


def meal_plan(p: "UserProfile", meals: dict) -> tuple[str, str]:  # type: ignore[name-defined]  # noqa: F821
    """
    Generate a detailed, professionally structured meal plan in Markdown.
    The meals dict is provided as grounding — model adds specific portions,
    timing, and preparation tips but cannot invent new food items.
    """
    b = "\n".join(f"  - {x}" for x in meals["breakfast"])
    lu = "\n".join(f"  - {x}" for x in meals["lunch"])
    d = "\n".join(f"  - {x}" for x in meals["dinner"])
    sn = "\n".join(f"  - {x}" for x in meals["snacks"])
    user = (
        f"{_profile_context(p)}\n\n"
        f"Approved meal options to work from:\n"
        f"Breakfast options:\n{b}\nLunch options:\n{lu}\nDinner options:\n{d}\nSnack options:\n{sn}\n\n"
        f"Generate a **detailed, professional daily meal plan** in Markdown for {p.name}. "
        f"Follow this exact structure:\n\n"
        f"## 🥗 Your Personalised Meal Plan\n"
        f"2-sentence intro mentioning {p.name}'s goal ({p.goal.replace('_', ' ')}) and diet preference ({p.dietary_pref or 'no restriction'}).\n\n"
        f"## 🌅 Breakfast\n"
        f"Pick ONE option from the approved breakfast list. Add:\n"
        f"- Specific serving size (e.g. '1 cup', '2 slices')\n"
        f"- Best time to eat (e.g. 'within 30 min of waking')\n"
        f"- 1 quick preparation tip\n\n"
        f"## ☀️ Lunch\n"
        f"Pick ONE option from the approved lunch list. Add serving size, timing, and 1 prep tip.\n\n"
        f"## 🌙 Dinner\n"
        f"Pick ONE option from the approved dinner list. Add serving size, timing, and 1 prep tip.\n\n"
        f"## 🍎 Snacks\n"
        f"Pick TWO options from the approved snack list. Add serving size and best time (e.g. pre/post workout).\n\n"
        f"## 💧 Hydration\n"
        f"Specific daily water intake guideline for {p.name} based on their activity level ({p.days_per_week} workout days).\n\n"
        f"## ✅ Nutrition Tips for {p.name}\n"
        f"3 specific, actionable nutrition tips aligned with {p.goal.replace('_', ' ')} and {p.dietary_pref or 'no dietary restriction'}. "
        f"Do NOT invent calorie counts or macro grams."
    )
    return SYSTEM, user


def motivation_message(p: "UserProfile", quote: str) -> tuple[str, str]:  # type: ignore[name-defined]  # noqa: F821
    """Generate a structured motivational message in Markdown."""
    user = (
        f"{_profile_context(p)}\n\n"
        f"Today's quote: \"{quote}\"\n\n"
        f"Generate a **professional motivational message** in Markdown for {p.name}. Structure:\n\n"
        f"## 🌟 Your Daily Motivation\n"
        f"Display the quote in a blockquote (> ).\n\n"
        f"## ✉️ A Message for {p.name}\n"
        f"3-4 sentences personalised to {p.name}'s {p.goal.replace('_', ' ')} journey and {p.motivation_style} motivation style. "
        f"Reference where they are in their journey specifically.\n\n"
        f"## 🎯 Today's Focus\n"
        f"ONE specific, actionable micro-goal for today based on their schedule ({p.days_per_week} days/week, {p.time_per_session} min).\n\n"
        f"Do NOT invent or attribute new quotes to real people."
    )
    return SYSTEM, user


def habit_plan(p: "UserProfile", tips: list[str]) -> tuple[str, str]:  # type: ignore[name-defined]  # noqa: F821
    """Generate a structured habit-building plan in Markdown."""
    tips_text = "\n".join(f"  - {t}" for t in tips)
    user = (
        f"{_profile_context(p)}\n\n"
        f"Approved habit tips:\n{tips_text}\n\n"
        f"Generate a **professional habit-building plan** in Markdown for {p.name}. Structure:\n\n"
        f"## 📅 Your Habit-Building Plan\n"
        f"2-sentence intro about why habits matter for {p.name}'s {p.goal.replace('_', ' ')} goal.\n\n"
        f"## ✅ Your Weekly Habit Checklist\n"
        f"For each approved tip, provide:\n"
        f"- **Habit**: the tip exactly as written\n"
        f"- **Why it matters**: 1 sentence specific to {p.name}'s profile (schedule/stress/goal)\n"
        f"- **How to start**: 1 tiny concrete action for today\n\n"
        f"## 📆 7-Day Kickstart Schedule\n"
        f"A simple day-by-day plan (Day 1–7) integrating these habits into {p.name}'s "
        f"{p.days_per_week}-day/week workout schedule.\n\n"
        f"Only reference the approved tips above. Do NOT add new habits."
    )
    return SYSTEM, user


def freeform_question(p: "UserProfile", question: str) -> tuple[str, str]:  # type: ignore[name-defined]  # noqa: F821
    """Answer a free-form question with a professionally structured Markdown response."""
    user = (
        f"{_profile_context(p)}\n\n"
        f"Question from {p.name}: {question}\n\n"
        f"Provide a **specific, professional answer** in Markdown. Structure:\n\n"
        f"## 💬 Answer\n"
        f"Direct, specific answer to the question (3-5 sentences), personalised to {p.name}'s profile above.\n\n"
        f"## 🔑 Key Points\n"
        f"3 bullet points with actionable takeaways specific to {p.name}'s level ({p.level}), "
        f"goal ({p.goal.replace('_', ' ')}), and schedule ({p.days_per_week} days/week).\n\n"
        f"## ⚠️ Important Note\n"
        f"Only include this section if the question involves injury, health conditions, or medical topics — "
        f"advise consulting a doctor. Otherwise omit this section.\n\n"
        f"Do NOT give medical diagnoses, specific supplement doses, or exact calorie/macro numbers."
    )
    return SYSTEM, user


def progress_feedback(
    p: "UserProfile", workouts: str, water: str, sleep: str, energy: str  # type: ignore[name-defined]  # noqa: F821
) -> tuple[str, str]:
    """Generate a structured weekly progress report in Markdown."""
    user = (
        f"{_profile_context(p)}\n\n"
        f"Weekly self-report:\n"
        f"- Workouts completed: {workouts} (target: {p.days_per_week}/week)\n"
        f"- Hydration goal met: {water}\n"
        f"- Average sleep: {sleep} hrs/night (usual: {p.sleep_hours} hrs)\n"
        f"- Energy level: {energy}/10\n\n"
        f"Generate a **professional weekly progress report** in Markdown. Structure:\n\n"
        f"## 📊 Weekly Progress Report — {p.name}\n\n"
        f"## 📈 Performance Summary\n"
        f"Table or bullets comparing this week's numbers vs {p.name}'s targets.\n\n"
        f"## ✅ What Went Well\n"
        f"Specific positive observations based only on the data above.\n\n"
        f"## 🔧 Areas to Improve\n"
        f"1-2 specific, actionable improvements for next week based on the gaps.\n\n"
        f"## 🎯 Next Week's Plan\n"
        f"3 concrete actions for next week tailored to {p.name}'s profile.\n\n"
        f"Base all feedback strictly on the self-reported data above. Do NOT invent numbers."
    )
    return SYSTEM, user


def onboarding_summary(p: "UserProfile") -> tuple[str, str]:  # type: ignore[name-defined]  # noqa: F821
    """Generate a warm personalised welcome in Markdown after onboarding."""
    user = (
        f"{_profile_context(p)}\n\n"
        f"Generate a **warm, professional welcome message** in Markdown for {p.name}. Structure:\n\n"
        f"## 👋 Welcome, {p.name}!\n"
        f"2 sentences acknowledging their {p.goal.replace('_', ' ')} goal and {p.level} level.\n\n"
        f"## 🗓️ Your Personalised Plan at a Glance\n"
        f"Bullet points summarising: workout schedule ({p.days_per_week} days × {p.time_per_session} min), "
        f"equipment ({p.equipment or 'bodyweight'}), diet ({p.dietary_pref or 'no restriction'}).\n\n"
        f"## 🚀 Your First Step Today\n"
        f"ONE specific action {p.name} can take right now, matching their {p.motivation_style} style.\n\n"
        f"Do NOT invent specific numbers or medical claims."
    )
    return SYSTEM, user
