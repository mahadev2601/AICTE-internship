"""
agent/prompts.py — Dynamic, modular LLM prompt templates for Fitness Buddy.

Uses structured JSON schemas and RAG context to generate truly personalized,
modular routines, adaptive meal plans, and safe conversational interactions.
Embeds strict medical guardrails, anti-hallucination constraints, and progressive
overload benchmarks.
"""

from __future__ import annotations

import json
from typing import Optional, Any

# ── Shared system persona with strict guardrails ──────────────────────────────
SYSTEM = (
    "You are Fitness Buddy, a professional, evidence-based AI health and fitness coach powered by IBM Granite. "
    "You provide modular, personalized guidance tailored to each user's unique profile, equipment, and health constraints. "
    "Always respond in clean Markdown with clear headings (##), bullet points (- ), and bold (**) for key terms. "
    "Be encouraging, motivational, and professional. Use emojis sparingly for section headers only. "
    "MANDATORY SAFETY RULES: "
    "1. You are NOT a doctor or physical therapist. NEVER diagnose medical conditions or prescribe physical therapy rehabilitation. "
    "2. If an exercise causes pain or the user has an injury, ALWAYS provide low-impact, joint-friendly modifications. "
    "3. NEVER fabricate calorie burns, exact macronutrient grams, or prescribe extreme diets (< 1200 kcal). "
    "4. NEVER recommend anabolic steroids, prescription weight-loss injections, or unverified supplement megadoses. "
    "5. If a question is outside fitness, exercise, and general nutrition scope, politely decline."
)


def _profile_context(p: Any, rag_context: str = "") -> str:
    """Build a rich profile context string combined with dynamic RAG telemetry."""
    base = (
        f"**Client Profile:**\n"
        f"- Name: {p.name} | Age: {p.age} | Gender: {p.gender}\n"
        f"- Height/Weight: {p.height} / {p.weight}\n"
        f"- Goal: {p.goal.replace('_', ' ').title()} | Level: {p.level.title()}\n"
        f"- Schedule: {p.days_per_week} days/week, {p.time_per_session} min/session\n"
        f"- Equipment: {p.equipment or 'none — bodyweight only'}\n"
        f"- Diet: {p.dietary_pref or 'no preference'}\n"
        f"- Health notes: {p.health_notes or 'none reported'}\n"
        f"- Sleep: {p.sleep_hours} hrs/night | Stress: {p.stress_level}/10\n"
        f"- Motivation style: {p.motivation_style}"
    )
    if rag_context:
        base += f"\n\n**Retrieved Memory & Historical Telemetry:**\n{rag_context}"
    return base


# ── Feature Prompts ───────────────────────────────────────────────────────────

def dynamic_workout_prompt(
    p: Any,
    modular_plan: dict[str, Any],
    user_feedback: str = "",
    rag_context: str = ""
) -> tuple[str, str]:
    """
    Generate a dynamic, modular workout plan.
    Exercises are dynamically filtered by available equipment and contraindications.
    """
    exercises_json = json.dumps([
        {
            "name": ex["name"],
            "movement": ex["movement_pattern"],
            "muscles": ex["muscle_groups"],
            "instructions": ex["instructions"],
            "cues": ex["cues"],
            "easier_regression": ex["regression"],
            "harder_progression": ex["progression"]
        }
        for ex in modular_plan.get("exercises", [])
    ], indent=2)

    feedback_notice = f"\nUser's real-time adjustment/request: '{user_feedback}'" if user_feedback else ""

    dur = modular_plan.get("duration_minutes", 30)
    warmup_time = "2 min" if dur <= 20 else "5 min"
    cooldown_time = "2 min" if dur <= 20 else "5 min"
    eq_list = ", ".join(modular_plan.get("equipment_used", ["bodyweight"]))

    user_msg = (
        f"{_profile_context(p, rag_context)}\n\n"
        f"⚡ REAL-TIME REQUEST OVERRIDE:\n"
        f"- Target Session Duration: {dur} minutes (CRITICAL: Use exactly {dur} minutes in your response, NOT the profile default of {p.time_per_session} min)\n"
        f"- Equipment to Use: {eq_list} (CRITICAL: Every main exercise MUST use {eq_list})\n"
        f"- User Feedback: '{user_feedback}'\n"
        f"- Active Injury Safeguards: {', '.join(modular_plan.get('active_contraindications', [])) or 'None'}{feedback_notice}\n\n"
        f"Modular Exercise Selection (grounded in safe catalog):\n{exercises_json}\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"1. You MUST generate a {dur}-minute routine matching {eq_list}.\n"
        f"2. You MUST use the exact exercises provided in the modular selection above.\n"
        f"3. Follow this exact structure:\n\n"
        f"## 💪 Your Personalised {dur}-Minute {eq_list.title()} Workout\n"
        f"2 warm sentences acknowledging their goal and confirming their {dur}-minute session with {eq_list}.\n\n"
        f"## 📋 Session Overview\n"
        f"- **Duration**: ~{dur} min | **Target Level**: {p.level.title()}\n"
        f"- **Equipment**: {eq_list}\n"
        f"- **Focus**: High-efficiency strength & functional mobility\n\n"
        f"## 🔥 Dynamic Warm-Up ({warmup_time})\n"
        + "\n".join(f"- {w}" for w in modular_plan.get("warmup", ["Arm circles (1 min)", "Hip openers (1 min)"])) +
        f"\n\n## 🏋️ Main Workout Circuit\n"
        f"For EACH exercise in the modular selection above, provide:\n"
        f"- **Exercise**: exact name\n"
        f"- **Target**: Sets × Reps ({'2-3 sets × 8-12 reps' if dur <= 20 else '3 sets × 10-12 reps'})\n"
        f"- **Rest**: recommended rest between sets ({'30-45s' if dur <= 20 else '45-60s'})\n"
        f"- **Form Tip**: 1 actionable technique cue\n"
        f"- **Safe Modification**: easier variation\n\n"
        f"## 🧊 Cool-Down & Recovery ({cooldown_time})\n"
        + "\n".join(f"- {c}" for c in modular_plan.get("cooldown", ["Chest stretch (1 min)", "Hamstring stretch (1 min)"])) +
        f"\n\n## 📈 Progressive Overload & Pro Tip for {p.name}\n"
        f"Explain how {p.name} can progressively overload this routine over the next 2-3 weeks.\n\n"
        f"> ⚠️ **Medical Disclaimer**: Listen to your body. If any movement causes sharp pain, discontinue immediately. Consult a physician before starting any strenuous exercise program."
    )
    return SYSTEM, user_msg



def dynamic_meal_prompt(
    p: Any,
    modular_plan: dict[str, Any],
    user_feedback: str = "",
    rag_context: str = ""
) -> tuple[str, str]:
    """Generate a dynamic, modular daily nutrition plan."""
    bf = modular_plan.get("breakfast", {})
    lu = modular_plan.get("lunch", {})
    di = modular_plan.get("dinner", {})
    sn = modular_plan.get("snacks", [])

    feedback_notice = f"\nUser's real-time dietary preference/request: '{user_feedback}'" if user_feedback else ""

    user_msg = (
        f"{_profile_context(p, rag_context)}\n\n"
        f"Dietary Constraint: {modular_plan.get('dietary_preference', 'no restriction')}\n"
        f"Goal: {modular_plan.get('goal', 'general_health')}{feedback_notice}\n\n"
        f"Curated Modular Meal Elements:\n"
        f"- Breakfast: {bf.get('name', 'Oats')} (Portion: {bf.get('portion_guidance', '1 bowl')})\n"
        f"- Lunch: {lu.get('name', 'Salad')} (Portion: {lu.get('portion_guidance', '1 plate')})\n"
        f"- Dinner: {di.get('name', 'Salmon')} (Portion: {di.get('portion_guidance', '1 fillet')})\n"
        f"- Snacks: {', '.join(s.get('name', '') for s in sn)}\n\n"
        f"Generate a **detailed, professional daily meal plan** in Markdown for {p.name}. "
        f"Follow this exact structure:\n\n"
        f"## 🥗 Your Personalised Nutrition Plan\n"
        f"2 sentences connecting their {p.goal.replace('_', ' ')} goal with wholesome nutrition habits.\n\n"
        f"## 🌅 Breakfast\n"
        f"- **Meal**: {bf.get('name')}\n"
        f"- **Portion & Timing**: {bf.get('portion_guidance')} eaten within 1-2 hours of waking\n"
        f"- **Easy Swap**: {bf.get('swap_option')}\n\n"
        f"## ☀️ Lunch\n"
        f"- **Meal**: {lu.get('name')}\n"
        f"- **Portion & Timing**: {lu.get('portion_guidance')} for sustained afternoon focus\n"
        f"- **Easy Swap**: {lu.get('swap_option')}\n\n"
        f"## 🌙 Dinner\n"
        f"- **Meal**: {di.get('name')}\n"
        f"- **Portion & Timing**: {di.get('portion_guidance')} at least 2-3 hours before sleep\n"
        f"- **Easy Swap**: {di.get('swap_option')}\n\n"
        f"## 🍎 Smart Snacks\n"
        + "\n".join(f"- **{s.get('name')}**: {s.get('portion_guidance')} (Swap: {s.get('swap_option')})" for s in sn) +
        f"\n\n## 💧 Daily Hydration Target\n"
        f"Guideline: Aim for ~{modular_plan.get('hydration_target_litres', 2.5)}L of water daily, adding 500ml on workout days.\n\n"
        f"## 💡 Actionable Nutrition Tips\n"
        f"2 specific habits tailored to {p.name}'s dietary preference ({p.dietary_pref or 'general'}) and {p.goal.replace('_', ' ')} goal.\n\n"
        f"> ⚠️ **Medical Disclaimer**: Nutritional advice is for educational wellness purposes. Consult a registered dietitian or physician for clinical diet therapy or food allergy management."
    )
    return SYSTEM, user_msg


def motivation_message(p: Any, quote: str, rag_context: str = "") -> tuple[str, str]:
    """Generate a structured motivational message in Markdown."""
    user_msg = (
        f"{_profile_context(p, rag_context)}\n\n"
        f"Today's quote: \"{quote}\"\n\n"
        f"Generate a **professional motivational message** in Markdown for {p.name}. Structure:\n\n"
        f"## 🌟 Your Daily Motivation\n"
        f"> {quote}\n\n"
        f"## ✉️ A Message for {p.name}\n"
        f"3-4 sentences personalised to {p.name}'s {p.goal.replace('_', ' ')} journey and {p.motivation_style} style. "
        f"Reference their consistency and weekly workout target ({p.days_per_week} days/week).\n\n"
        f"## 🎯 Today's Micro-Goal\n"
        f"ONE specific, actionable micro-goal for today (e.g. drinking an extra glass of water or doing 5 minutes of mobility).\n\n"
        f"Do NOT invent or attribute new quotes to real people."
    )
    return SYSTEM, user_msg


def habit_plan(p: Any, tips: list[str], rag_context: str = "") -> tuple[str, str]:
    """Generate a structured habit-building plan in Markdown."""
    tips_text = "\n".join(f"  - {t}" for t in tips)
    user_msg = (
        f"{_profile_context(p, rag_context)}\n\n"
        f"Approved habit tips:\n{tips_text}\n\n"
        f"Generate a **professional habit-building plan** in Markdown for {p.name}. Structure:\n\n"
        f"## 📅 Your Habit-Building Plan\n"
        f"2-sentence intro about compounding consistency for {p.name}'s {p.goal.replace('_', ' ')} goal.\n\n"
        f"## ✅ Your Weekly Habit Checklist\n"
        f"For each tip, provide:\n"
        f"- **Habit**: exact tip\n"
        f"- **Why it matters**: 1 sentence for their schedule and stress level ({p.stress_level}/10)\n"
        f"- **Action step**: 1 tiny immediate step for today\n\n"
        f"## 📆 7-Day Kickstart Schedule\n"
        f"Day-by-day plan (Day 1–7) integrating habits with their {p.days_per_week}-day workout schedule."
    )
    return SYSTEM, user_msg


def freeform_question(
    p: Any,
    question: str,
    rag_context: str = "",
    coaching_guidance: str = ""
) -> tuple[str, str]:
    """Answer a free-form question with RAG grounding and clinical boundary enforcement."""
    guidance_block = f"\nSafety & Boundary Guidance:\n{coaching_guidance}\n" if coaching_guidance else ""

    user_msg = (
        f"{_profile_context(p, rag_context)}\n\n"
        f"Question from {p.name}: {question}\n{guidance_block}\n"
        f"Provide a **specific, professional answer** in Markdown. Structure:\n\n"
        f"## 💬 Fitness Buddy Advice\n"
        f"Direct, actionable answer (3-5 sentences) personalised to {p.name}'s profile and fitness level ({p.level}).\n\n"
        f"## 🔑 Key Actionable Takeaways\n"
        f"3 concise bullet points with practical tips.\n\n"
        f"## ⚠️ Important Health Note\n"
        f"If the question touches on pain, injuries, or health conditions, advise consulting a physician or physical therapist. "
        f"Otherwise keep this note brief reminding them to train with proper form."
    )
    return SYSTEM, user_msg


def progress_feedback(
    p: Any,
    workouts: str,
    water: str,
    sleep: str,
    energy: str,
    rag_context: str = ""
) -> tuple[str, str]:
    """Generate a structured weekly progress report in Markdown."""
    user_msg = (
        f"{_profile_context(p, rag_context)}\n\n"
        f"Weekly Self-Report Data:\n"
        f"- Workouts completed: {workouts} (Target: {p.days_per_week} sessions)\n"
        f"- Hydration goal met: {water}\n"
        f"- Average sleep: {sleep} hrs/night (Baseline: {p.sleep_hours} hrs)\n"
        f"- Energy level: {energy}/10\n\n"
        f"Generate a **professional weekly progress report** in Markdown. Structure:\n\n"
        f"## 📊 Weekly Progress Report — {p.name}\n\n"
        f"## 📈 Performance Summary\n"
        f"Table or bullets comparing self-reported data against targets.\n\n"
        f"## ✅ Wins & Positive Momentum\n"
        f"Specific positive observations based on the data.\n\n"
        f"## 🔧 Optimization Focus for Next Week\n"
        f"1-2 concrete adjustments to bridge gaps in workout target, sleep, or hydration.\n\n"
        f"## 🎯 Action Plan\n"
        f"3 simple, actionable commitments for the upcoming week."
    )
    return SYSTEM, user_msg


def onboarding_summary(p: Any) -> tuple[str, str]:
    """Generate a warm personalised welcome in Markdown after onboarding."""
    user_msg = (
        f"{_profile_context(p)}\n\n"
        f"Generate a **warm, professional welcome message** in Markdown for {p.name}. Structure:\n\n"
        f"## 👋 Welcome to Fitness Buddy, {p.name}!\n"
        f"2 encouraging sentences acknowledging their {p.goal.replace('_', ' ')} goal and {p.level} level.\n\n"
        f"## 🗓️ Your Plan Blueprint\n"
        f"- **Schedule**: {p.days_per_week} days/week × {p.time_per_session} minutes\n"
        f"- **Equipment**: {p.equipment or 'Bodyweight exercises'}\n"
        f"- **Nutrition Focus**: Aligned with {p.dietary_pref or 'balanced eating'}\n\n"
        f"## 🚀 Your First Step Today\n"
        f"ONE specific, zero-friction action {p.name} can take today matching their {p.motivation_style} motivation style."
    )
    return SYSTEM, user_msg


# ── Legacy compatibility wrappers ─────────────────────────────────────────────
def workout_plan(p: Any, plan_key: str, routine: list[str]) -> tuple[str, str]:
    """Legacy wrapper for backward compatibility."""
    from data.knowledge_bank import assemble_modular_workout
    modular = assemble_modular_workout(p)
    return dynamic_workout_prompt(p, modular)


def meal_plan(p: Any, meals: dict) -> tuple[str, str]:
    """Legacy wrapper for backward compatibility."""
    from data.knowledge_bank import assemble_modular_meal_plan
    modular = assemble_modular_meal_plan(p)
    return dynamic_meal_prompt(p, modular)
