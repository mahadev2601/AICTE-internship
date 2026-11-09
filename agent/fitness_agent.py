"""
agent/fitness_agent.py — Dynamic, Modular FitnessBuddy Conversational Agent.

Features:
1. Dynamic, modular routines and meal plans powered by the knowledge catalog.
2. Robust SQLite persistence for profiles, progressive overload, and check-ins.
3. Moderation and medical guardrails with emergency red-flag interception.
4. Intelligent context window management (sliding window + RAG + rolling summarization).
"""

from __future__ import annotations

import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Any

import data.quotes as quote_data
import agent.prompts as prompts
from data.database import db
from data.knowledge_bank import (
    assemble_modular_workout,
    assemble_modular_meal_plan,
    search_knowledge_bank,
)
from agent.guardrails import SafetyGuard, MANDATORY_DISCLAIMER
from agent.context_manager import context_mgr
from agent.model import generate, init_model
from config import APP_NAME, APP_VERSION


@dataclass
class UserProfile:
    """
    Complete user profile for deep personalisation.
    All fields have safe defaults so the agent works even with partial data.
    """
    name:             str = "Champion"
    age:              str = "unknown"
    gender:           str = "prefer not to say"

    height:           str = "not provided"
    weight:           str = "not provided"

    goal:             str = "general_health"   # weight_loss | muscle_gain | general_health | endurance
    level:            str = "beginner"         # beginner | intermediate | advanced
    days_per_week:    str = "3"
    time_per_session: str = "30"               # minutes

    equipment:        str = ""                 # e.g. "dumbbells, resistance bands"
    dietary_pref:     str = ""                 # e.g. "vegetarian", "vegan", "no pref"
    health_notes:     str = ""                 # e.g. "bad knees", "diabetes"
    sleep_hours:      str = "7"
    stress_level:     str = "5"                # 1-10

    motivation_style: str = "encouragement"   # encouragement | challenge | data-driven | community

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        valid = {k: str(v) for k, v in d.items() if k in cls.__dataclass_fields__ and v is not None}
        return cls(**valid)


class FitnessBuddy:
    """
    Main conversational agent for Fitness Buddy.
    Integrates dynamic modular generation, SQLite state, safety guardrails, and RAG.
    """

    def __init__(self, database=None) -> None:
        self.model = init_model()
        self.db = database or db
        self.context_mgr = context_mgr
        self.profile = UserProfile()

        # Load first existing profile from DB if available
        all_profiles = self.db.list_all_profiles()
        if all_profiles:
            first_key = next(iter(all_profiles))
            self.profile = UserProfile.from_dict(all_profiles[first_key])

    # ── Greeting ─────────────────────────────────────────────────────────────
    def greet(self) -> str:
        hour = datetime.now().hour
        time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        mode = "IBM Granite AI" if self.model else "offline mode (modular dynamic engine)"
        return (
            f"\n{'='*62}\n"
            f"  {APP_NAME} v{APP_VERSION} — Your AI Health Coach  [{mode}]\n"
            f"{'='*62}\n"
            f"  Good {time_of_day}! I am your personal Fitness Buddy.\n"
            f"  Equipped with dynamic modular routines, progressive overload tracking,\n"
            f"  strict safety guardrails, and intelligent contextual memory.\n"
            f"{'='*62}\n"
        )

    # ── Profile Persistence ──────────────────────────────────────────────────
    def set_profile(self, profile: UserProfile) -> None:
        """Update active profile and persist directly to SQLite database."""
        self.profile = profile
        self.db.save_profile(profile.to_dict())

    def load_profile_by_name(self, name: str) -> bool:
        """Load profile from database by user name."""
        data = self.db.get_profile(name)
        if data:
            self.profile = UserProfile.from_dict(data)
            return True
        return False

    # ── CLI Onboarding ────────────────────────────────────────────────────────
    def collect_profile(self) -> str:
        """Interactive CLI onboarding."""
        print("\n  Let's personalise your experience! (Press Enter to skip any question)\n")

        name = input("  1. What's your name? ").strip() or "Champion"
        age  = input("  2. How old are you? ").strip() or "unknown"

        print("  3. Gender:")
        genders = {"1": "male", "2": "female", "3": "non-binary", "4": "prefer not to say"}
        for k, v in genders.items():
            print(f"       {k}. {v.title()}")
        gender = genders.get(input("     Choice (1-4): ").strip(), "prefer not to say")

        height = input("  4. Height (e.g. 5'8\" or 173cm, optional): ").strip() or "not provided"
        weight = input("  5. Weight (e.g. 70kg, optional): ").strip() or "not provided"

        print("  6. Primary fitness goal:")
        goals = {"1": "weight_loss", "2": "muscle_gain", "3": "general_health", "4": "endurance"}
        for k, v in goals.items():
            print(f"       {k}. {v.replace('_', ' ').title()}")
        goal = goals.get(input("     Choice (1-4): ").strip(), "general_health")

        print("  7. Current fitness level:")
        levels = {"1": "beginner", "2": "intermediate", "3": "advanced"}
        for k, v in levels.items():
            print(f"       {k}. {v.title()}")
        level = levels.get(input("     Choice (1-3): ").strip(), "beginner")

        days = input("  8. How many days per week can you work out? (default 3): ").strip() or "3"
        time = input("  9. How many minutes per session? (default 30): ").strip() or "30"
        equipment = input("  10. Any equipment at home? (e.g. dumbbells, bands — or blank): ").strip()

        print("  11. Dietary preference:")
        diets = {"1": "no preference", "2": "vegetarian", "3": "vegan", "4": "gluten-free", "5": "lactose-free"}
        for k, v in diets.items():
            print(f"       {k}. {v.title()}")
        dietary_pref = diets.get(input("     Choice (1-5): ").strip(), "no preference")

        health_notes = input("  12. Any injuries or health conditions we should know? (e.g. bad knees): ").strip()
        sleep_hours  = input("  13. Average sleep hours per night? (default 7): ").strip() or "7"
        stress_level = input("  14. Stress level this week (1-10)? (default 5): ").strip() or "5"

        print("  15. What keeps you motivated?")
        styles = {"1": "encouragement", "2": "challenge", "3": "data-driven", "4": "community"}
        for k, v in styles.items():
            print(f"       {k}. {v.title()}")
        motivation_style = styles.get(input("     Choice (1-4): ").strip(), "encouragement")

        self.profile = UserProfile(
            name=name, age=age, gender=gender,
            height=height, weight=weight,
            goal=goal, level=level,
            days_per_week=days, time_per_session=time,
            equipment=equipment, dietary_pref=dietary_pref,
            health_notes=health_notes, sleep_hours=sleep_hours,
            stress_level=stress_level, motivation_style=motivation_style,
        )
        self.set_profile(self.profile)

        system, user = prompts.onboarding_summary(self.profile)
        fallback = (
            f"## 👋 Welcome, {name}!\n\n"
            f"I've tailored your personalised routine around your **{goal.replace('_',' ')}** goal and **{level}** level.\n"
            f"With **{days} days/week** and **{time} minutes per session**, you're set up for sustainable success. Let's crush it! 💪"
        )
        welcome = generate(self.model, system, user, fallback)
        print(f"\n  {'='*58}\n  {welcome}\n  {'='*58}\n")
        return welcome

    # ── 1. Dynamic Modular Workout ────────────────────────────────────────────
    def show_workout(self, user_feedback: str = "") -> str:
        """
        Generate a dynamic, modular workout routine tailored to current constraints,
        available equipment, injury safeguards, and progressive overload targets.
        """
        p = self.profile

        # Assemble modular routine from safe catalog
        modular = assemble_modular_workout(p, user_feedback=user_feedback)

        # Retrieve RAG telemetry: progressive overload benchmarks & recent workouts
        rag_context = self.context_mgr.retrieve_relevant_fitness_context(p, intent="workout", query=user_feedback)

        # Build prompt
        system, user = prompts.dynamic_workout_prompt(p, modular, user_feedback, rag_context)

        # Build offline fallback from modular catalog
        exercises_md = []
        for ex in modular["exercises"]:
            exercises_md.append(
                f"### 🏋️ {ex['name']}\n"
                f"- **Movement Pattern**: {ex['movement_pattern'].title()} | **Muscles**: {', '.join(ex['muscle_groups'])}\n"
                f"- **Target**: 3 sets × 10-12 reps (rest 45-60s)\n"
                f"- **Form Cue**: {ex['cues']}\n"
                f"- **Modification / Joint Safety**: {ex['regression']}"
            )

        dur = modular["duration_minutes"]
        warmup_time = "2 min" if dur <= 20 else "5 min"
        cooldown_time = "2 min" if dur <= 20 else "5 min"
        eq_str = ", ".join(modular["equipment_used"])

        fallback = (
            f"## 💪 Your Personalised {dur}-Minute {eq_str.title()} Workout\n\n"
            f"Custom routine prepared for **{p.name}** | Goal: **{p.goal.replace('_',' ').title()}** | Duration: **~{dur} min**\n\n"
            f"## 📋 Session Overview\n"
            f"- **Target Duration**: ~{dur} min | **Target Level**: {p.level.title()}\n"
            f"- **Equipment In Use**: {eq_str}\n"
            f"- **Active Health Considerations**: {p.health_notes or 'None reported'}\n\n"
            f"## 🔥 Dynamic Warm-Up ({warmup_time})\n"
            + "\n".join(f"- {w}" for w in modular["warmup"]) +
            f"\n\n## 🏋️ Main Workout Circuit\n\n"
            + "\n\n".join(exercises_md) +
            f"\n\n## 🧊 Cool-Down & Mobility ({cooldown_time})\n"
            + "\n".join(f"- {c}" for c in modular["cooldown"]) +
            f"\n\n## 📈 Progressive Overload Guidance\n"
            f"- Focus on quality technique first.\n"
            f"- Once you can hit 12 clean reps for all sets, increase to 14 reps or add a slight pause at peak tension.\n"
            f"- Log your weights and reps after each session to track your progressive overload!"
            + MANDATORY_DISCLAIMER
        )


        response = generate(self.model, system, user, fallback)
        return SafetyGuard.sanitize_output(response, disclaimer_required=True)

    # ── 2. Dynamic Modular Meal Plan ──────────────────────────────────────────
    def show_meal_plan(self, user_feedback: str = "") -> str:
        """Generate a dynamic, modular meal plan aligned with dietary preference and goal."""
        p = self.profile

        modular = assemble_modular_meal_plan(p, user_feedback=user_feedback)
        rag_context = self.context_mgr.retrieve_relevant_fitness_context(p, intent="meal", query=user_feedback)

        system, user = prompts.dynamic_meal_prompt(p, modular, user_feedback, rag_context)

        bf = modular["breakfast"]
        lu = modular["lunch"]
        di = modular["dinner"]
        sn = modular["snacks"]

        fallback = (
            f"## 🥗 Your Personalised Nutrition Plan\n\n"
            f"Tailored for **{p.name}** | Goal: **{p.goal.replace('_',' ').title()}** | Diet: **{p.dietary_pref or 'No restriction'}**\n\n"
            f"## 🌅 Breakfast\n"
            f"- **{bf['name']}**\n"
            f"- **Portion Guidance**: {bf['portion_guidance']} (Prep: ~{bf['approx_prep_min']} min)\n"
            f"- **Swap Option**: {bf['swap_option']}\n\n"
            f"## ☀️ Lunch\n"
            f"- **{lu['name']}**\n"
            f"- **Portion Guidance**: {lu['portion_guidance']} (Prep: ~{lu['approx_prep_min']} min)\n"
            f"- **Swap Option**: {lu['swap_option']}\n\n"
            f"## 🌙 Dinner\n"
            f"- **{di['name']}**\n"
            f"- **Portion Guidance**: {di['portion_guidance']} (Prep: ~{di['approx_prep_min']} min)\n"
            f"- **Swap Option**: {di['swap_option']}\n\n"
            f"## 🍎 Smart Snacks\n"
            + "\n".join(f"- **{s['name']}**: {s['portion_guidance']} (Swap: {s['swap_option']})" for s in sn) +
            f"\n\n## 💧 Hydration Target\n"
            f"- Aim for **{modular['hydration_target_litres']} litres** of water today, plus an extra 500ml during exercise sessions."
            + MANDATORY_DISCLAIMER
        )

        response = generate(self.model, system, user, fallback)
        return SafetyGuard.sanitize_output(response, disclaimer_required=True)

    # ── 3. Motivation ─────────────────────────────────────────────────────────
    def show_motivation(self) -> str:
        p = self.profile
        quote = random.choice(quote_data.MOTIVATIONAL_QUOTES)
        rag_context = self.context_mgr.retrieve_relevant_fitness_context(p, intent="motivation")

        system, user = prompts.motivation_message(p, quote, rag_context)
        fallback = (
            f"## 🌟 Your Daily Motivation\n\n"
            f"> {quote}\n\n"
            f"## ✉️ A Message for {p.name}\n\n"
            f"Every workout is a vote for the person you are becoming. "
            f"Your **{p.goal.replace('_',' ')}** goal is within reach — stay consistent!\n\n"
            f"## 🎯 Today's Micro-Goal\n\n"
            f"- {random.choice(quote_data.HABIT_TIPS)}"
        )
        return generate(self.model, system, user, fallback)

    # ── 4. Habit Tips ─────────────────────────────────────────────────────────
    def show_habit_tips(self) -> str:
        p = self.profile
        tips = random.sample(quote_data.HABIT_TIPS, k=min(4, len(quote_data.HABIT_TIPS)))
        rag_context = self.context_mgr.retrieve_relevant_fitness_context(p, intent="habit")

        system, user = prompts.habit_plan(p, tips, rag_context)
        fallback = (
            f"## 📅 Your Habit-Building Blueprint\n\n"
            f"Small daily habits compound into massive long-term results, {p.name}.\n\n"
            f"## ✅ Core Weekly Habits\n\n"
            + "\n".join(f"- **{tip}**" for tip in tips)
        )
        return generate(self.model, system, user, fallback)

    # ── 5. Free-form Q&A with Safety Guardrails & Conversational Memory ───────
    def ask_question(self, question: str, session_id: str = "default") -> str:
        """
        Process a user question with:
        1. Safety moderation & emergency symptom detection.
        2. Clinical boundary enforcement.
        3. Dynamic RAG retrieval (exercise/nutrition knowledge + progressive overload history).
        4. Conversational memory persistence.
        """
        p = self.profile

        # 1. Moderation & Guardrail Screen
        guard_res = SafetyGuard.evaluate_input(question, p)
        if not guard_res.is_safe and guard_res.intercept_response:
            # Emergency symptom or clinical violation intercepted
            self.db.save_chat_message(p.name, "user", question, "safety_intercept", session_id)
            self.db.save_chat_message(p.name, "assistant", guard_res.intercept_response, "safety_intercept", session_id)
            return guard_res.intercept_response

        # 2. Retrieve dynamic context via RAG
        rag_context = self.context_mgr.retrieve_relevant_fitness_context(p, intent="freeform", query=question)

        # 3. Retrieve recent conversation sliding window
        recent_turns = self.context_mgr.get_sliding_window_history(p.name, limit=4)
        if recent_turns:
            history_block = "\n".join(f"{t['role'].capitalize()}: {t['message'][:120]}" for t in recent_turns)
            rag_context = f"{rag_context}\n\n**Recent Chat History:**\n{history_block}".strip()

        # 4. Generate response
        system, user = prompts.freeform_question(
            p, question, rag_context=rag_context, coaching_guidance=guard_res.coaching_guidance
        )
        fallback = (
            f"## 💬 Fitness Buddy Guidance\n\n"
            f"Great question, {p.name}! For best results with your **{p.goal.replace('_', ' ')}** goal, "
            f"focus on consistency across your **{p.days_per_week}-day schedule**.\n\n"
            f"## 🔑 Key Points\n\n"
            f"- Prioritise controlled form and gradual progression over heavy weights\n"
            f"- Ensure you're sleeping {p.sleep_hours} hours to support muscle recovery\n"
            f"- Listen to your body and adjust intensity whenever needed\n"
            f"\n> ⚠️ **Health Note**: If you experience persistent joint discomfort or pain, please consult a certified healthcare professional."
        )

        response = generate(self.model, system, user, fallback)
        final_response = SafetyGuard.sanitize_output(response, disclaimer_required=guard_res.disclaimer_required)

        # 5. Persist to SQLite conversational memory
        self.db.save_chat_message(p.name, "user", question, "freeform", session_id)
        self.db.save_chat_message(p.name, "assistant", final_response, "freeform", session_id)

        # 6. Periodically compress memory summary in the background
        self.context_mgr.update_conversation_summary(p.name, self.model)

        return final_response

    # ── 6. Progress Check-in ──────────────────────────────────────────────────
    def progress_checkin(
        self,
        workouts: Optional[str] = None,
        water: Optional[str] = None,
        sleep: Optional[str] = None,
        energy: Optional[str] = None
    ) -> str:
        """Record check-in telemetry and return personalised progress feedback."""
        p = self.profile

        if workouts is None:
            # Interactive CLI mode
            print(f"\n  PROGRESS CHECK-IN — {p.name} (target: {p.days_per_week} workouts/week)")
            print(f"  {'─'*55}")
            workouts = input("  Workouts completed this week          : ").strip() or "0"
            water    = input("  Hydration goal met most days? (yes/no): ").strip() or "unknown"
            sleep    = input("  Avg sleep hrs/night this week         : ").strip() or p.sleep_hours
            energy   = input("  Energy level this week (1-10)         : ").strip() or "5"

        rag_context = self.context_mgr.retrieve_relevant_fitness_context(p, intent="checkin")
        system, user = prompts.progress_feedback(p, workouts, water, sleep, energy, rag_context)

        fallback = (
            f"## 📊 Weekly Progress Report — {p.name}\n\n"
            f"## 📈 Performance Summary\n\n"
            f"- **Workouts**: {workouts}/{p.days_per_week} target sessions completed\n"
            f"- **Hydration**: {water}\n"
            f"- **Sleep**: {sleep} hrs/night (Baseline: {p.sleep_hours} hrs)\n"
            f"- **Energy Level**: {energy}/10\n\n"
            f"## 🎯 Focus for Next Week\n\n"
            f"- Keep showing up for your scheduled {p.days_per_week} sessions\n"
            f"- Aim for steady hydration and restorative sleep\n"
            f"- Consistency compounds into lasting fitness transformations!"
        )

        feedback = generate(self.model, system, user, fallback)
        clean_feedback = SafetyGuard.sanitize_output(feedback, disclaimer_required=False)

        # Log into SQLite database
        self.db.log_checkin(
            p.name, workouts, p.days_per_week, water, sleep, energy, ai_feedback=clean_feedback
        )

        return clean_feedback

    # ── 7. Workout Logging & Progressive Overload ─────────────────────────────
    def log_workout_set(
        self,
        exercise_name: str,
        sets: int,
        reps: int,
        weight_kg: float = 0.0,
        duration_sec: int = 0,
        rpe: int = 7,
        notes: str = ""
    ) -> str:
        """Record completed exercise data and calculate progressive overload."""
        p = self.profile
        self.db.log_workout(
            p.name, exercise_name, sets, reps, weight_kg, duration_sec, rpe, notes
        )
        return (
            f"✅ Logged **{exercise_name}**: {sets} sets × {reps} reps "
            f"({'@ ' + str(weight_kg) + 'kg' if weight_kg > 0 else 'bodyweight'}). "
            f"Progressive overload targets updated!"
        )

    def get_progressive_overload_report(self) -> str:
        """Generate a progressive overload progress summary."""
        p = self.profile
        overload = self.db.get_progressive_overload_summary(p.name)
        if not overload:
            return (
                f"## 📈 Progressive Overload Tracker — {p.name}\n\n"
                f"No workouts logged yet. Complete your first session and log your sets to begin tracking progressive overload!"
            )

        rows = []
        for item in overload:
            last_wt = f"{item['last_weight_kg']} kg" if item['last_weight_kg'] > 0 else "Bodyweight"
            max_wt = f"{item['max_weight_kg']} kg" if item['max_weight_kg'] > 0 else "Bodyweight"
            rows.append(
                f"| **{item['exercise']}** | {last_wt} × {item['last_reps']} reps | {max_wt} × {item['max_reps']} reps | `{item['recommended_target']}` |"
            )

        return (
            f"## 📈 Progressive Overload Tracker — {p.name}\n\n"
            f"Tracking strength progression and recommending next session benchmarks:\n\n"
            f"| Exercise | Last Session | Personal Best | Next Target |\n"
            f"|:---|:---|:---|:---|\n"
            + "\n".join(rows) +
            f"\n\n> 💡 **Coach Tip**: Progressive overload means challenging your muscles just slightly more than last time — by adding 1-2 reps, increasing weight, or slowing down your tempo."
        )
