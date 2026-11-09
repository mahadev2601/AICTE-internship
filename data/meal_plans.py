"""
data/meal_plans.py — Curated, nutritionist-aligned meal ideas per fitness goal.

Keeping meal content static prevents the AI from inventing calorie counts,
macros, or unsafe dietary advice. The agent adds only a short contextual tip.
"""

from typing import TypedDict, Any, Optional


class MealPlan(TypedDict):
    breakfast: list[str]
    lunch: list[str]
    dinner: list[str]
    snacks: list[str]


PLANS: dict[str, MealPlan] = {
    "weight_loss": {
        "breakfast": [
            "Oatmeal with berries and chia seeds",
            "Greek yogurt with banana and honey",
            "Scrambled eggs with spinach and whole-grain toast",
        ],
        "lunch": [
            "Grilled chicken salad with olive oil dressing",
            "Lentil soup with multigrain bread",
            "Quinoa bowl with roasted veggies and chickpeas",
        ],
        "dinner": [
            "Baked salmon with steamed broccoli and sweet potato",
            "Tofu stir-fry with brown rice",
            "Lean beef with sauteed greens and cauliflower mash",
        ],
        "snacks": [
            "Apple with almond butter",
            "Handful of mixed nuts",
            "Carrot sticks with hummus",
            "Low-fat cottage cheese with cucumber",
        ],
    },
    "muscle_gain": {
        "breakfast": [
            "4-5 eggs with oats and banana smoothie",
            "Protein pancakes with peanut butter",
            "Greek yogurt parfait with granola and mixed fruits",
        ],
        "lunch": [
            "Rice with grilled chicken and avocado",
            "Whole-wheat pasta with turkey meatballs",
            "Tuna sandwich on multigrain with side salad",
        ],
        "dinner": [
            "Beef steak with sweet potato and asparagus",
            "Salmon with quinoa and mixed veggies",
            "Chicken thighs with roasted potatoes and broccoli",
        ],
        "snacks": [
            "Protein shake with milk",
            "Peanut butter rice cakes",
            "Hard-boiled eggs",
            "Cheese with whole-grain crackers",
        ],
    },
    "general_health": {
        "breakfast": [
            "Overnight oats with flaxseed and berries",
            "Whole-wheat toast with avocado and egg",
            "Smoothie: spinach, banana, almond milk, protein powder",
        ],
        "lunch": [
            "Mediterranean wrap with hummus and veggies",
            "Brown rice bowl with edamame and miso dressing",
            "Caprese salad with whole-grain bread",
        ],
        "dinner": [
            "Grilled fish tacos with mango salsa",
            "Vegetable curry with basmati rice",
            "Stuffed bell peppers with lean mince and veggies",
        ],
        "snacks": [
            "Fresh fruit salad",
            "Trail mix (nuts, seeds, dried berries)",
            "Celery with hummus",
            "Dark chocolate (70%+) with a handful of almonds",
        ],
    },
}

# Goals without a specific plan fall back to general_health
_FALLBACK = "general_health"


def get_plan(goal: str) -> tuple[str, MealPlan]:
    """Return (plan_key, plan) for the given goal. Falls back to general_health."""
    key = goal if goal in PLANS else _FALLBACK
    return key, PLANS[key]


def get_dynamic_meal_plan(profile: Any, user_feedback: str = "", dietary_pref: Optional[str] = None) -> dict[str, Any]:
    """
    Generate a dynamic, modular meal plan aligned with dietary preference and goal.
    Delegates to the modular knowledge bank.
    """
    from data.knowledge_bank import assemble_modular_meal_plan
    return assemble_modular_meal_plan(profile, user_feedback=user_feedback, dietary_pref=dietary_pref)

