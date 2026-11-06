"""
agent/fitness_agent.py — FitnessBuddy conversational agent.

Fully personalised: every response is grounded in the user's complete
profile (age, gender, goal, level, time, equipment, diet, health, sleep,
stress, motivation style) collected during onboarding.
"""

from __future__ import annotations

import random
from datetime import datetime
from dataclasses import dataclass, field

import data.meal_plans    as meal_data
import data.workout_plans as workout_data
import data.quotes        as quote_data
import agent.prompts      as prompts
from agent.model import generate, init_model
from config import APP_NAME, APP_VERSION


@dataclass
class UserProfile:
    """
    Complete user profile for deep personalisation.
    All fields have safe defaults so the agent works even with partial data.
    """
    # ── Basic info ──────────────────────────────────────────────────────────
    name:             str = "Champion"
    age:              str = "unknown"
    gender:           str = "prefer not to say"

    # ── Body metrics (optional, no calculations done — just context for AI) ─
    height:           str = "not provided"
    weight:           str = "not provided"

    # ── Fitness parameters ──────────────────────────────────────────────────
    goal:             str = "general_health"   # weight_loss | muscle_gain | general_health | endurance
    level:            str = "beginner"         # beginner | intermediate | advanced
    days_per_week:    str = "3"
    time_per_session: str = "30"               # minutes

    # ── Lifestyle ───────────────────────────────────────────────────────────
    equipment:        str = ""                 # e.g. "dumbbells, resistance bands"
    dietary_pref:     str = ""                 # e.g. "vegetarian", "vegan", "no pref"
    health_notes:     str = ""                 # e.g. "bad knees", "diabetes" → AI advises doctor
    sleep_hours:      str = "7"
    stress_level:     str = "5"               # 1-10

    # ── Motivation style ────────────────────────────────────────────────────
    motivation_style: str = "encouragement"   # encouragement | challenge | data-driven | community

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class FitnessBuddy:
    """
    Main conversational agent for Fitness Buddy.

    - IBM Granite model is initialised once at construction.
    - Every feature method uses the full UserProfile to personalise responses.
    - All model calls go through agent.model.generate() — never raises.
    """

    def __init__(self) -> None:
        self.model   = init_model()
        self.profile = UserProfile()

    # ── Greeting ─────────────────────────────────────────────────────────────
    def greet(self) -> str:
        hour = datetime.now().hour
        time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        mode = "IBM Granite AI" if self.model else "offline"
        return (
            f"\n{'='*62}\n"
            f"  {APP_NAME} v{APP_VERSION} — Your AI Health Coach  [{mode}]\n"
            f"{'='*62}\n"
            f"  Good {time_of_day}! I am your personal Fitness Buddy.\n"
            f"  I will create a plan built entirely around YOU — your goals,\n"
            f"  your schedule, your lifestyle. No gym required.\n"
            f"{'='*62}\n"
        )

    # ── Rich onboarding ───────────────────────────────────────────────────────
    def collect_profile(self) -> str:
        """
        Interactive CLI onboarding. Asks 12 personalisation questions.
        Returns a personalised welcome message from IBM Granite.
        """
        print("\n  Let's personalise your experience! (Press Enter to skip any question)\n")

        # ── Basic ─────────────────────────────────────────────────────────
        name = input("  1. What's your name? ").strip() or "Champion"

        age  = input("  2. How old are you? ").strip() or "unknown"

        print("  3. Gender:")
        genders = {"1": "male", "2": "female", "3": "non-binary", "4": "prefer not to say"}
        for k, v in genders.items():
            print(f"       {k}. {v.title()}")
        gender = genders.get(input("     Choice (1-4): ").strip(), "prefer not to say")

        # ── Body (optional) ───────────────────────────────────────────────
        height = input("  4. Height (e.g. 5'8\" or 173cm, optional): ").strip() or "not provided"
        weight = input("  5. Weight (e.g. 70kg, optional): ").strip() or "not provided"

        # ── Fitness goal ──────────────────────────────────────────────────
        print("  6. Primary fitness goal:")
        goals = {
            "1": "weight_loss",
            "2": "muscle_gain",
            "3": "general_health",
            "4": "endurance",
        }
        for k, v in goals.items():
            print(f"       {k}. {v.replace('_', ' ').title()}")
        goal = goals.get(input("     Choice (1-4): ").strip(), "general_health")

        # ── Fitness level ─────────────────────────────────────────────────
        print("  7. Current fitness level:")
        levels = {"1": "beginner", "2": "intermediate", "3": "advanced"}
        for k, v in levels.items():
            print(f"       {k}. {v.title()}")
        level = levels.get(input("     Choice (1-3): ").strip(), "beginner")

        # ── Schedule ──────────────────────────────────────────────────────
        days = input("  8. How many days per week can you work out? (default 3): ").strip() or "3"
        time = input("  9. How many minutes per session? (default 30): ").strip() or "30"

        # ── Equipment ─────────────────────────────────────────────────────
        equipment = input("  10. Any equipment at home? (e.g. dumbbells, bands — or leave blank): ").strip()

        # ── Diet ──────────────────────────────────────────────────────────
        print("  11. Dietary preference:")
        diets = {
            "1": "no preference",
            "2": "vegetarian",
            "3": "vegan",
            "4": "gluten-free",
            "5": "lactose-free",
        }
        for k, v in diets.items():
            print(f"       {k}. {v.title()}")
        dietary_pref = diets.get(input("     Choice (1-5): ").strip(), "no preference")

        # ── Health notes ──────────────────────────────────────────────────
        health_notes = input("  12. Any injuries or health conditions we should know? (optional): ").strip()

        # ── Lifestyle ─────────────────────────────────────────────────────
        sleep_hours  = input("  13. Average sleep hours per night? (default 7): ").strip() or "7"
        stress_level = input("  14. Stress level this week (1=low, 10=high)? (default 5): ").strip() or "5"

        # ── Motivation style ──────────────────────────────────────────────
        print("  15. What keeps you motivated?")
        styles = {
            "1": "encouragement",
            "2": "challenge",
            "3": "data-driven",
            "4": "community",
        }
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

        # Generate a personalised welcome using IBM Granite
        system, user = prompts.onboarding_summary(self.profile)
        fallback = (
            f"Welcome, {name}! I've built your personalised plan around your {goal.replace('_',' ')} "
            f"goal and {level} level. With {days} days/week and {time} minutes per session, "
            f"you're all set — let's get started!"
        )
        welcome = generate(self.model, system, user, fallback)
        print(f"\n  {'='*58}")
        print(f"  {welcome}")
        print(f"  {'='*58}\n")
        return welcome

    # ── 1. Workout plan ───────────────────────────────────────────────────────
    def show_workout(self) -> str:
        p = self.profile
        plan_key, plan = workout_data.get_plan(p.goal, p.level)

        system, user = prompts.workout_plan(p, plan_key, plan["routine"])
        fallback = (
            f"## 💪 Your {plan_key.replace('_',' ').title()} Workout Plan\n\n"
            f"Here is your personalised plan, {p.name}!\n\n"
            f"## 📋 Plan Overview\n"
            f"- **Duration**: {plan['duration']}  |  **Target**: {p.time_per_session} min/session\n"
            f"- **Frequency**: {plan['frequency']}  |  **Your schedule**: {p.days_per_week} days/week\n"
            f"- **Equipment**: {p.equipment or 'none — bodyweight only'}\n"
            f"- **Goal**: {p.goal.replace('_',' ').title()}\n\n"
            f"## 🏋️ Today's Routine\n"
            + "\n".join(f"- {step}" for step in plan["routine"]) +
            (f"\n\n> ⚠️ **Health Note**: You mentioned '{p.health_notes}' — skip or modify any exercise that causes discomfort. Consult a doctor if needed." if p.health_notes else "") +
            f"\n\n## 💡 Tip\n- {random.choice(quote_data.HABIT_TIPS)}"
        )
        return generate(self.model, system, user, fallback)

    # ── 2. Meal plan ──────────────────────────────────────────────────────────
    def show_meal_plan(self) -> str:
        p = self.profile
        plan_key, meals = meal_data.get_plan(p.goal)

        system, user = prompts.meal_plan(p, meals)
        fallback = (
            f"## 🥗 Your Personalised Meal Plan\n\n"
            f"Tailored for **{p.name}** | Goal: **{p.goal.replace('_',' ').title()}** | Diet: **{p.dietary_pref or 'no preference'}**\n\n"
            f"## 🌅 Breakfast\n" + "\n".join(f"- {x}" for x in meals["breakfast"]) +
            f"\n\n## ☀️ Lunch\n" + "\n".join(f"- {x}" for x in meals["lunch"]) +
            f"\n\n## 🌙 Dinner\n" + "\n".join(f"- {x}" for x in meals["dinner"]) +
            f"\n\n## 🍎 Snacks\n" + "\n".join(f"- {x}" for x in meals["snacks"]) +
            f"\n\n## 💧 Hydration\nAim for **8–10 glasses** of water daily. Add an extra glass for each workout session."
        )
        return generate(self.model, system, user, fallback)

    # ── 3. Daily motivation ───────────────────────────────────────────────────
    def show_motivation(self) -> str:
        p     = self.profile
        quote = random.choice(quote_data.MOTIVATIONAL_QUOTES)

        system, user = prompts.motivation_message(p, quote)
        fallback = (
            f"## 🌟 Your Daily Motivation\n\n"
            f"> {quote}\n\n"
            f"## ✉️ A Message for {p.name}\n\n"
            f"Every workout is a vote for the person you are becoming. "
            f"Your **{p.goal.replace('_',' ')}** goal is within reach — keep showing up!\n\n"
            f"## 🎯 Today's Focus\n\n"
            f"- {random.choice(quote_data.HABIT_TIPS)}"
        )
        return generate(self.model, system, user, fallback)

    # ── 4. Habit tips ─────────────────────────────────────────────────────────
    def show_habit_tips(self) -> str:
        p    = self.profile
        tips = random.sample(quote_data.HABIT_TIPS, k=5)

        system, user = prompts.habit_plan(p, tips)
        fallback = (
            f"## 📅 Your Habit-Building Plan\n\n"
            f"Small daily habits compound into life-changing results, {p.name}. "
            f"With your {p.days_per_week}-day schedule, consistency is your greatest advantage.\n\n"
            f"## ✅ Your Weekly Habit Checklist\n\n"
            + "\n".join(f"- **{tip}**" for tip in tips)
        )
        return generate(self.model, system, user, fallback)

    # ── 5. Free-form Q&A ──────────────────────────────────────────────────────
    def ask_question(self, question: str) -> str:
        p = self.profile

        system, user = prompts.freeform_question(p, question)
        fallback = (
            f"## 💬 Answer\n\n"
            f"Great question, {p.name}! For personalised advice on that topic, "
            f"I'd recommend consulting a certified fitness trainer or nutritionist.\n\n"
            f"## 🔑 Key Points\n\n"
            f"- Stay consistent with your {p.days_per_week}-day workout schedule\n"
            f"- Focus on your **{p.goal.replace('_', ' ')}** goal one step at a time\n"
            f"- Your **{p.level}** level means gradual, safe progression is key"
        )
        return generate(self.model, system, user, fallback)

    # ── 6. Progress check-in ──────────────────────────────────────────────────
    def progress_checkin(self) -> str:
        p = self.profile
        print(f"\n  PROGRESS CHECK-IN  — {p.name} (target: {p.days_per_week} workouts/week)")
        print(f"  {'─'*55}")
        workouts = input("  Workouts completed this week          : ").strip() or "0"
        water    = input("  Hydration goal met most days? (yes/no): ").strip() or "unknown"
        sleep    = input("  Avg sleep hrs/night this week         : ").strip() or p.sleep_hours
        energy   = input("  Energy level this week (1-10)         : ").strip() or "5"

        system, user = prompts.progress_feedback(p, workouts, water, sleep, energy)
        fallback = (
            f"## 📊 Weekly Progress Report — {p.name}\n\n"
            f"## 📈 Performance Summary\n\n"
            f"- **Workouts**: {workouts}/{p.days_per_week} target sessions\n"
            f"- **Hydration**: {water}\n"
            f"- **Sleep**: {sleep} hrs/night (usual: {p.sleep_hours} hrs)\n"
            f"- **Energy**: {energy}/10\n\n"
            f"## 🎯 Next Week's Plan\n\n"
            f"- Keep pushing towards your {p.days_per_week} workout target\n"
            f"- Prioritise sleep if below {p.sleep_hours} hrs\n"
            f"- Consistency is your greatest asset, {p.name}!"
        )
        return generate(self.model, system, user, fallback)
