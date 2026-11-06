"""
data/workout_plans.py — Curated, expert-reviewed home workout plans.

All content is static and human-authored. The AI agent is instructed
to reference these plans rather than generating exercises from scratch,
which eliminates hallucinated exercise names or unsafe rep counts.
"""

from typing import TypedDict


class WorkoutPlan(TypedDict):
    description: str
    frequency: str
    duration: str
    routine: list[str]


PLANS: dict[str, WorkoutPlan] = {
    "beginner": {
        "description": "Perfect for those just starting out. Focus on form and building consistency.",
        "frequency": "3 days/week (Mon · Wed · Fri)",
        "duration": "~30 minutes",
        "routine": [
            "Warm-up       : 5 min brisk walk or light jog in place",
            "Push-ups       : 3 sets x 8 reps (knees on ground if needed)",
            "Bodyweight Squats : 3 sets x 12 reps",
            "Plank Hold     : 3 x 20 seconds",
            "Glute Bridges  : 3 sets x 12 reps",
            "Jumping Jacks  : 3 sets x 20 reps",
            "Cool-down      : 5 min gentle stretching",
        ],
    },
    "intermediate": {
        "description": "For those with 3-6 months of consistent training.",
        "frequency": "4 days/week",
        "duration": "~45 minutes",
        "routine": [
            "Warm-up           : 10 min dynamic stretches + jumping jacks",
            "Push-ups          : 4 sets x 15 reps",
            "Jump Squats       : 4 sets x 12 reps",
            "Dumbbell Rows     : 3 sets x 12 reps each side (or water-bottle rows)",
            "Plank             : 3 x 45 seconds",
            "Lunges            : 3 sets x 10 reps each leg",
            "Burpees           : 3 sets x 10 reps",
            "Cool-down         : 10 min yoga-inspired stretching",
        ],
    },
    "advanced": {
        "description": "High-intensity plan for experienced fitness enthusiasts.",
        "frequency": "5 days/week",
        "duration": "~60 minutes",
        "routine": [
            "Warm-up           : 10 min HIIT (high knees + butt kicks + arm circles)",
            "Decline Push-ups  : 4 sets x 20 reps",
            "Pistol Squats     : 4 sets x 8 reps each leg",
            "Weighted Rows     : 4 sets x 12 reps",
            "Dynamic Plank     : 3 x 60 seconds (rock forward/back)",
            "Plyometric Lunges : 4 sets x 12 reps each side",
            "Burpees           : 4 sets x 15 reps",
            "Sprint Intervals  : 6 x 30-second all-out sprints",
            "Cool-down         : 15 min full-body stretch",
        ],
    },
    "weight_loss": {
        "description": "Cardio-focused plan to burn calories and build lean muscle.",
        "frequency": "5-6 days/week",
        "duration": "~50 minutes",
        "routine": [
            "Warm-up           : 5 min jump rope or marching in place",
            "HIIT Circuit      : 3 rounds, 45 sec on / 15 sec off",
            "  -> High Knees -> Squat Jumps -> Mountain Climbers -> Push-ups",
            "Steady Cardio     : 20 min brisk walk/jog",
            "Reverse Lunges    : 3 sets x 12 each leg",
            "Core Circuit      : Bicycle Crunches + Leg Raises x 3 rounds",
            "Cool-down         : 10 min stretching",
        ],
    },
    "muscle_gain": {
        "description": "Resistance-focused plan for building strength and muscle mass.",
        "frequency": "4 days/week (push/pull/legs split)",
        "duration": "~55 minutes",
        "routine": [
            "Warm-up           : 5 min light cardio + shoulder/hip mobility",
            "Push              : Push-ups 4x15, Pike Push-ups 3x12",
            "Pull              : Resistance Band Rows 4x12, Chin-ups or Door Rows 3x10",
            "Legs              : Bulgarian Split Squats 4x10, Romanian Deadlift 3x12",
            "Compound Carry    : Farmer's Walk with heavy bags 3x30 sec",
            "Cool-down         : 10 min stretching + mobility",
        ],
    },
}

# Maps a user's stated goal to a plan key
GOAL_TO_PLAN: dict[str, str] = {
    "weight_loss":   "weight_loss",
    "muscle_gain":   "muscle_gain",
    "general_health": "beginner",   # default to beginner level for general health
    "endurance":     "intermediate",
}


def get_plan(goal: str, level: str) -> tuple[str, WorkoutPlan]:
    """
    Return (plan_key, plan) for the given goal and fitness level.
    Goal-specific plans take priority over level-based plans.
    """
    if goal in ("weight_loss", "muscle_gain"):
        key = goal
    else:
        key = level if level in PLANS else "beginner"
    return key, PLANS[key]
