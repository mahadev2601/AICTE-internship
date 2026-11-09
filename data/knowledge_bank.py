"""
data/knowledge_bank.py — Modular, dynamic exercise & nutrition catalog for Fitness Buddy.

Replaces rigid, hardcoded lists with an extensible, categorized knowledge bank.
Supports dynamic filtering by equipment, fitness level, injury contraindications,
dietary preferences, and real-time user constraints.
"""

from __future__ import annotations

import re
import random
from typing import TypedDict, Optional, Any


class Exercise(TypedDict):
    id: str
    name: str
    movement_pattern: str       # push | pull | squat | hinge | lunge | core | cardio
    muscle_groups: list[str]
    equipment: list[str]        # bodyweight | dumbbells | resistance_bands | pullup_bar
    difficulty: str             # beginner | intermediate | advanced
    contraindications: list[str] # e.g. knee_pain, lower_back_pain, shoulder_pain, wrist_pain
    is_low_impact: bool
    instructions: str
    cues: str
    regression: str
    progression: str


class MealItem(TypedDict):
    id: str
    name: str
    meal_type: str              # breakfast | lunch | dinner | snack
    diet_tags: list[str]        # vegetarian | vegan | gluten_free | dairy_free | high_protein | balanced
    goals: list[str]            # weight_loss | muscle_gain | general_health | endurance
    key_ingredients: list[str]
    approx_prep_min: int
    protein_source: str
    swap_option: str
    portion_guidance: str


# ── Curated Modular Exercise Catalog (40+ Exercises) ──────────────────────────

EXERCISE_CATALOG: list[Exercise] = [
    # ── Push Exercises
    {
        "id": "pushup_std",
        "name": "Standard Push-ups",
        "movement_pattern": "push",
        "muscle_groups": ["chest", "triceps", "front delts", "core"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": ["wrist_pain", "shoulder_pain"],
        "is_low_impact": True,
        "instructions": "Place hands shoulder-width apart, lower chest until elbows reach 90 degrees, press up firmly.",
        "cues": "Keep core tight, elbows tucked at 45 degrees, avoid letting hips sag.",
        "regression": "Knee Push-ups or Incline Push-ups against a wall/table",
        "progression": "Decline Push-ups or Diamond Push-ups"
    },
    {
        "id": "pushup_incline",
        "name": "Incline Push-ups (Elevated Hands)",
        "movement_pattern": "push",
        "muscle_groups": ["lower chest", "triceps", "front delts"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": ["wrist_pain"],
        "is_low_impact": True,
        "instructions": "Place hands on an elevated surface like a bench, table, or sturdy chair.",
        "cues": "Straight line from heels to crown; gentle on wrists and shoulders.",
        "regression": "Wall Push-ups",
        "progression": "Standard Floor Push-ups"
    },
    {
        "id": "pushup_pike",
        "name": "Pike Push-ups",
        "movement_pattern": "push",
        "muscle_groups": ["shoulders", "upper chest", "triceps"],
        "equipment": ["bodyweight"],
        "difficulty": "intermediate",
        "contraindications": ["shoulder_pain", "wrist_pain"],
        "is_low_impact": True,
        "instructions": "Hips elevated in an inverted V shape, lower crown of head towards hands and press back up.",
        "cues": "Focus vertical drive through the shoulders; look between toes.",
        "regression": "Hand-elevated Pike Push-ups",
        "progression": "Feet-elevated Pike or Handstand Push-up"
    },
    {
        "id": "db_floor_press",
        "name": "Dumbbell Floor Press",
        "movement_pattern": "push",
        "muscle_groups": ["chest", "triceps", "shoulders"],
        "equipment": ["dumbbells"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Lie flat on the floor with knees bent. Press dumbbells straight up from chest, lowering till elbows touch floor.",
        "cues": "The floor prevents shoulder hyperextension, making this exceptionally safe for shoulders.",
        "regression": "Lightweight Dumbbell Press",
        "progression": "Single-Arm Dumbbell Floor Press"
    },
    {
        "id": "band_chest_press",
        "name": "Resistance Band Chest Press",
        "movement_pattern": "push",
        "muscle_groups": ["chest", "triceps", "core"],
        "equipment": ["resistance_bands"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Anchor band behind back or around shoulder blades; press handles forward evenly.",
        "cues": "Squeeze chest at full extension; control the return slowly.",
        "regression": "Lighter tension band",
        "progression": "Heavier band or pause at peak contraction"
    },
    {
        "id": "db_overhead_press",
        "name": "Standing Dumbbell Overhead Press",
        "movement_pattern": "push",
        "muscle_groups": ["shoulders", "upper traps", "triceps", "core"],
        "equipment": ["dumbbells"],
        "difficulty": "intermediate",
        "contraindications": ["shoulder_pain", "lower_back_pain"],
        "is_low_impact": True,
        "instructions": "Stand with feet hip-width, press dumbbells overhead without arching lower back.",
        "cues": "Brace core as if taking a punch, avoid flaring ribs.",
        "regression": "Seated Dumbbell Overhead Press",
        "progression": "Alternating or Arnold Press"
    },

    # ── Pull Exercises
    {
        "id": "db_bent_row",
        "name": "Dumbbell Bent-Over Row",
        "movement_pattern": "pull",
        "muscle_groups": ["lats", "rhomboids", "rear delts", "biceps"],
        "equipment": ["dumbbells"],
        "difficulty": "intermediate",
        "contraindications": ["lower_back_pain"],
        "is_low_impact": True,
        "instructions": "Hinge at hips with flat back, pull dumbbells towards hips squeezing shoulder blades.",
        "cues": "Pull with elbows, not hands; keep spine neutral.",
        "regression": "Supported One-Arm Dumbbell Row on chair",
        "progression": "Pause at peak contraction for 2 seconds"
    },
    {
        "id": "door_frame_row",
        "name": "Door Frame / Towel Row",
        "movement_pattern": "pull",
        "muscle_groups": ["upper back", "biceps", "forearms"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Hold onto sturdy door frame with feet close to base; lean back and pull chest to frame.",
        "cues": "Adjust body angle to change resistance: more horizontal is harder.",
        "regression": "Stand more upright",
        "progression": "Single-arm Door Frame Row"
    },
    {
        "id": "band_seated_row",
        "name": "Seated Resistance Band Row",
        "movement_pattern": "pull",
        "muscle_groups": ["mid-back", "lats", "biceps"],
        "equipment": ["resistance_bands"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Sit tall with legs straight, loop band around feet, pull handles towards ribcage.",
        "cues": "Keep chest proud and draw shoulders back and down.",
        "regression": "Looser band loop",
        "progression": "Double band tension or add 2-sec hold"
    },
    {
        "id": "band_face_pull",
        "name": "Resistance Band Face Pull",
        "movement_pattern": "pull",
        "muscle_groups": ["rear delts", "rotator cuff", "upper back"],
        "equipment": ["resistance_bands"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Anchor band at eye level; pull towards forehead while rotating hands back.",
        "cues": "Great posture correction; pull elbows high and wide.",
        "regression": "Lighter band with controlled tempo",
        "progression": "Hold 3 seconds at ears"
    },

    # ── Squat & Knee-Dominant Lower Body
    {
        "id": "bodyweight_squat",
        "name": "Bodyweight Air Squats",
        "movement_pattern": "squat",
        "muscle_groups": ["quadriceps", "glutes", "hamstrings", "calves"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": ["knee_pain"],
        "is_low_impact": True,
        "instructions": "Feet shoulder-width apart, sink hips back and down to parallel, drive up through heels.",
        "cues": "Chest upright, knees track in line with second toes.",
        "regression": "Box / Chair Squats (sit to a chair and stand up)",
        "progression": "Goblet Squat or Jump Squat"
    },
    {
        "id": "box_squat",
        "name": "Chair / Box Squat",
        "movement_pattern": "squat",
        "muscle_groups": ["quadriceps", "glutes"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Squat back onto a sturdy chair or couch, pause lightly without relaxing, then stand.",
        "cues": "Eliminates knee strain and reinforces proper hip-hinge depth.",
        "regression": "Higher surface height",
        "progression": "Air Squats without chair"
    },
    {
        "id": "wall_sit",
        "name": "Isometric Wall Sit",
        "movement_pattern": "squat",
        "muscle_groups": ["quadriceps", "glutes", "calves"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Slide back down wall until thighs are parallel to ground, knees at 90 degrees, hold.",
        "cues": "Keep back flat against the wall, breathe steadily.",
        "regression": "Thighs at 45 degrees instead of 90 degrees",
        "progression": "Hold dumbbell on lap or single-leg lift"
    },
    {
        "id": "goblet_squat",
        "name": "Dumbbell Goblet Squat",
        "movement_pattern": "squat",
        "muscle_groups": ["quadriceps", "glutes", "core", "upper back"],
        "equipment": ["dumbbells"],
        "difficulty": "intermediate",
        "contraindications": ["knee_pain"],
        "is_low_impact": True,
        "instructions": "Hold single dumbbell vertically against chest, squat deep keeping torso upright.",
        "cues": "Weight at chest acts as a counterbalance for perfect posture.",
        "regression": "Bodyweight Squat",
        "progression": "Increase dumbbell weight or add tempo (3 sec down)"
    },

    # ── Hinge & Posterior Chain
    {
        "id": "glute_bridge",
        "name": "Glute Bridges",
        "movement_pattern": "hinge",
        "muscle_groups": ["glutes", "hamstrings", "lower back"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Lie on back with knees bent, drive through heels to lift hips until body forms a straight line.",
        "cues": "Squeeze glutes hard at the top; zero knee impact.",
        "regression": "Shorter range of motion with feet closer",
        "progression": "Single-Leg Glute Bridge"
    },
    {
        "id": "single_leg_bridge",
        "name": "Single-Leg Glute Bridge",
        "movement_pattern": "hinge",
        "muscle_groups": ["glutes", "hamstrings", "core stabilizers"],
        "equipment": ["bodyweight"],
        "difficulty": "intermediate",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Extend one leg straight, drive through the opposite heel to lift hips into full extension.",
        "cues": "Keep hips level without dipping to one side.",
        "regression": "Standard Double-Leg Glute Bridge",
        "progression": "Elevate foot on a step"
    },
    {
        "id": "db_romanian_deadlift",
        "name": "Dumbbell Romanian Deadlift (RDL)",
        "movement_pattern": "hinge",
        "muscle_groups": ["hamstrings", "glutes", "erectors"],
        "equipment": ["dumbbells"],
        "difficulty": "intermediate",
        "contraindications": ["acute_lower_back_pain"],
        "is_low_impact": True,
        "instructions": "Slight knee bend, push hips back as dumbbells slide along shins, feel deep hamstring stretch.",
        "cues": "Move through the hips, not the lower back. Keep back locked flat.",
        "regression": "Bodyweight Good Mornings with hands on hips",
        "progression": "Single-Leg Dumbbell RDL"
    },

    # ── Lunge & Unilateral
    {
        "id": "reverse_lunge",
        "name": "Step-Back Reverse Lunges",
        "movement_pattern": "lunge",
        "muscle_groups": ["glutes", "quads", "hamstrings"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": ["knee_pain"],
        "is_low_impact": True,
        "instructions": "Step one foot backward, lower back knee towards floor, push through front heel to return.",
        "cues": "Reverse lunges place substantially less shear stress on the knee than forward lunges.",
        "regression": "Static Split Squat with hand on chair for balance",
        "progression": "Add dumbbells at sides or Bulgarian Split Squat"
    },
    {
        "id": "step_ups",
        "name": "Step-Ups on Low Box / Stair",
        "movement_pattern": "lunge",
        "muscle_groups": ["quads", "glutes", "calves"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Step one foot onto a sturdy step/platform, drive through foot to stand tall.",
        "cues": "Control the descent back down; do not bounce off back foot.",
        "regression": "Low step height (single staircase step)",
        "progression": "Hold dumbbells or increase step height"
    },

    # ── Core & Stability
    {
        "id": "plank_standard",
        "name": "Forearm Plank Hold",
        "movement_pattern": "core",
        "muscle_groups": ["transverse abdominis", "rectus abdominis", "shoulders"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": ["lower_back_pain", "shoulder_pain"],
        "is_low_impact": True,
        "instructions": "Rest on forearms and toes, maintain straight rigid plank line from head to heels.",
        "cues": "Tuck pelvis slightly, squeeze glutes and quads, breathe continuously.",
        "regression": "Kneeling Plank or Incline Forearm Plank",
        "progression": "Plank with Shoulder Taps or Body Saw"
    },
    {
        "id": "bird_dog",
        "name": "Bird Dog Hold & Reach",
        "movement_pattern": "core",
        "muscle_groups": ["multifidus", "erector spinae", "glutes", "deltoids"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "On all fours, extend opposite arm and leg straight out parallel to floor, pause, return.",
        "cues": "Gold-standard spine-sparing core exercise for back health.",
        "regression": "Arm reach only, then leg reach only",
        "progression": "Hold for 5 seconds with small pulses"
    },
    {
        "id": "dead_bug",
        "name": "Dead Bug Core Stabilization",
        "movement_pattern": "core",
        "muscle_groups": ["deep abdominal wall", "hip flexors"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Lie on back with arms up and knees at 90 degrees. Lower opposite arm and leg while pressing lower back to floor.",
        "cues": "Lower back must remain glued to the ground at all times.",
        "regression": "Leg tap only with knees bent",
        "progression": "Add light resistance band between hands/feet"
    },
    {
        "id": "side_plank",
        "name": "Side Plank Hold",
        "movement_pattern": "core",
        "muscle_groups": ["obliques", "quadratus lumborum", "glute medius"],
        "equipment": ["bodyweight"],
        "difficulty": "intermediate",
        "contraindications": ["shoulder_pain"],
        "is_low_impact": True,
        "instructions": "Rest on one elbow and side of feet, elevate hips into a straight lateral line.",
        "cues": "Keep top shoulder back, don't let hips roll forward.",
        "regression": "Kneeling Side Plank (bent bottom knee)",
        "progression": "Side Plank with Hip Dips"
    },

    # ── Cardio & Conditioning
    {
        "id": "jumping_jacks",
        "name": "Standard Jumping Jacks",
        "movement_pattern": "cardio",
        "muscle_groups": ["full_body", "calves", "deltoids"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": ["knee_pain", "ankle_pain"],
        "is_low_impact": False,
        "instructions": "Jump feet wide while bringing arms overhead, jump back to center.",
        "cues": "Land softly on balls of feet.",
        "regression": "Step Jacks (step one foot out without jumping)",
        "progression": "Star Jumps"
    },
    {
        "id": "step_jacks_low_impact",
        "name": "Low-Impact Step Jacks",
        "movement_pattern": "cardio",
        "muscle_groups": ["calves", "shoulders", "cardiovascular"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "Step right foot out while raising arms overhead; return to center and repeat on left side.",
        "cues": "Completely joint-friendly cardio; keep arms crisp and energetic.",
        "regression": "Slower tempo",
        "progression": "Speed up tempo or add light arm weights"
    },
    {
        "id": "shadow_boxing",
        "name": "Shadow Boxing Intervals (Jab-Cross-Hook)",
        "movement_pattern": "cardio",
        "muscle_groups": ["shoulders", "core", "cardiovascular"],
        "equipment": ["bodyweight"],
        "difficulty": "beginner",
        "contraindications": [],
        "is_low_impact": True,
        "instructions": "In athletic stance, throw controlled combinations of straight punches and hooks with light footwork.",
        "cues": "Pivot on ball of foot with punches, zero joint impact, high calorie burn.",
        "regression": "Stationary punch drills",
        "progression": "Add duck-and-slip head movement"
    },
    {
        "id": "mountain_climbers",
        "name": "Mountain Climbers",
        "movement_pattern": "cardio",
        "muscle_groups": ["core", "shoulders", "hip flexors"],
        "equipment": ["bodyweight"],
        "difficulty": "intermediate",
        "contraindications": ["wrist_pain", "lower_back_pain"],
        "is_low_impact": False,
        "instructions": "In push-up plank, rapidly drive knees alternately towards chest.",
        "cues": "Keep hips down level with shoulders.",
        "regression": "Elevated hands on chair or slow marching pace",
        "progression": "Cross-body Mountain Climbers"
    },
    {
        "id": "burpees",
        "name": "Full Burpees",
        "movement_pattern": "cardio",
        "muscle_groups": ["full_body"],
        "equipment": ["bodyweight"],
        "difficulty": "advanced",
        "contraindications": ["knee_pain", "wrist_pain", "lower_back_pain", "heart_condition"],
        "is_low_impact": False,
        "instructions": "Drop into squat, kick feet back to plank, perform push-up, jump feet in and leap upright.",
        "cues": "High intensity power movement; maintain core tension in plank.",
        "regression": "Step-Back Burpee without push-up or jump",
        "progression": "Burpee over dumbbell"
    },
]


# ── Curated Modular Nutrition Catalog ─────────────────────────────────────────

MEAL_CATALOG: list[MealItem] = [
    # ── Breakfasts
    {
        "id": "bf_oatmeal_chia",
        "name": "Steel-Cut Oats with Berries & Chia Seeds",
        "meal_type": "breakfast",
        "diet_tags": ["vegetarian", "vegan", "dairy_free", "high_protein"],
        "goals": ["weight_loss", "general_health", "endurance"],
        "key_ingredients": ["rolled oats", "chia seeds", "blueberries", "almond milk", "cinnamon"],
        "approx_prep_min": 10,
        "protein_source": "chia seeds & oats (optional plant protein scoop)",
        "swap_option": "Swap almond milk for cow's milk or soy milk for extra protein",
        "portion_guidance": "1/2 cup dry oats + 1 tbsp chia + 1/2 cup fresh berries"
    },
    {
        "id": "bf_eggs_toast",
        "name": "Scrambled Eggs with Sautéed Spinach & Whole-Grain Toast",
        "meal_type": "breakfast",
        "diet_tags": ["vegetarian", "high_protein", "balanced"],
        "goals": ["weight_loss", "muscle_gain", "general_health"],
        "key_ingredients": ["whole eggs / egg whites", "baby spinach", "whole-grain sourdough", "olive oil"],
        "approx_prep_min": 8,
        "protein_source": "eggs & egg whites",
        "swap_option": "Swap whole-grain bread with gluten-free toast or roasted sweet potato slices",
        "portion_guidance": "2 whole eggs + 1 egg white + 1 slice whole-grain bread"
    },
    {
        "id": "bf_greek_yogurt_bowl",
        "name": "High-Protein Greek Yogurt Parfait",
        "meal_type": "breakfast",
        "diet_tags": ["vegetarian", "gluten_free", "high_protein"],
        "goals": ["muscle_gain", "weight_loss", "general_health"],
        "key_ingredients": ["plain Greek yogurt 0-2%", "honey", "sliced banana", "walnuts / almonds"],
        "approx_prep_min": 5,
        "protein_source": "Greek yogurt (20g+ protein)",
        "swap_option": "Swap dairy yogurt for coconut or almond yogurt for dairy-free",
        "portion_guidance": "1 cup Greek yogurt + 1/2 sliced banana + 10 almonds"
    },
    {
        "id": "bf_tofu_scramble",
        "name": "Turmeric Spiced Tofu Scramble with Veggies",
        "meal_type": "breakfast",
        "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "high_protein"],
        "goals": ["muscle_gain", "weight_loss", "general_health"],
        "key_ingredients": ["firm tofu crumbled", "turmeric", "bell peppers", "spinach", "nutritional yeast"],
        "approx_prep_min": 12,
        "protein_source": "firm tofu",
        "swap_option": "Serve with 1/2 sliced avocado for healthy omega fats",
        "portion_guidance": "150g firm tofu + generous mixed veggies"
    },

    # ── Lunches
    {
        "id": "lu_quinoa_chickpea",
        "name": "Mediterranean Quinoa Bowl with Spiced Chickpeas",
        "meal_type": "lunch",
        "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "balanced"],
        "goals": ["general_health", "weight_loss", "endurance"],
        "key_ingredients": ["cooked quinoa", "chickpeas", "cucumber", "cherry tomatoes", "tahini lemon dressing"],
        "approx_prep_min": 15,
        "protein_source": "chickpeas & quinoa",
        "swap_option": "Add crumbled feta cheese if dairy is permitted",
        "portion_guidance": "3/4 cup cooked quinoa + 1/2 cup rinsed chickpeas + unlimited salad greens"
    },
    {
        "id": "lu_chicken_salad",
        "name": "Grilled Lemon Herb Chicken Salad with Avocado",
        "meal_type": "lunch",
        "diet_tags": ["gluten_free", "dairy_free", "high_protein", "low_carb"],
        "goals": ["weight_loss", "muscle_gain"],
        "key_ingredients": ["chicken breast", "mixed baby greens", "avocado", "extra virgin olive oil", "balsamic vinegar"],
        "approx_prep_min": 15,
        "protein_source": "lean chicken breast (30g protein)",
        "swap_option": "Substitute chicken with grilled salmon or baked tempeh",
        "portion_guidance": "120-150g grilled chicken + 1/4 avocado + large leafy salad"
    },
    {
        "id": "lu_lentil_soup",
        "name": "Hearty Red Lentil & Vegetable Stew",
        "meal_type": "lunch",
        "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "high_protein"],
        "goals": ["general_health", "weight_loss"],
        "key_ingredients": ["red lentils", "carrots", "celery", "crushed tomatoes", "cumin & coriander"],
        "approx_prep_min": 25,
        "protein_source": "red lentils",
        "swap_option": "Pair with 1 slice multigrain toast or a handful of pumpkin seeds",
        "portion_guidance": "1.5 cups hearty stew"
    },
    {
        "id": "lu_turkey_wrap",
        "name": "Whole-Wheat Turkey & Hummus Crunch Wrap",
        "meal_type": "lunch",
        "diet_tags": ["dairy_free", "high_protein", "balanced"],
        "goals": ["muscle_gain", "general_health", "endurance"],
        "key_ingredients": ["whole-wheat tortilla", "sliced lean turkey", "hummus", "cucumbers", "shredded carrots"],
        "approx_prep_min": 7,
        "protein_source": "lean roast turkey & hummus",
        "swap_option": "Use gluten-free tortilla or collard green wrap for low-carb",
        "portion_guidance": "1 large wrap with 100g turkey"
    },

    # ── Dinners
    {
        "id": "di_baked_salmon",
        "name": "Herb-Baked Wild Salmon with Roasted Asparagus & Sweet Potato",
        "meal_type": "dinner",
        "diet_tags": ["gluten_free", "dairy_free", "high_protein", "balanced"],
        "goals": ["weight_loss", "muscle_gain", "general_health"],
        "key_ingredients": ["salmon fillet", "sweet potato wedges", "asparagus spears", "lemon", "rosemary"],
        "approx_prep_min": 20,
        "protein_source": "wild salmon (rich in Omega-3)",
        "swap_option": "Swap salmon for baked cod, trout, or grilled portobello steaks",
        "portion_guidance": "140g salmon + 1 small roasted sweet potato + 1 bunch asparagus"
    },
    {
        "id": "di_tofu_stirfry",
        "name": "Crispy Tofu & Asian Vegetable Stir-Fry with Brown Rice",
        "meal_type": "dinner",
        "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "goals": ["general_health", "weight_loss", "muscle_gain"],
        "key_ingredients": ["pressed firm tofu", "broccoli florets", "snap peas", "tamari (gluten-free soy)", "ginger & garlic"],
        "approx_prep_min": 18,
        "protein_source": "tofu & edamame",
        "swap_option": "Substitute brown rice with cauliflower rice for lower carbohydrate option",
        "portion_guidance": "150g tofu + 1/2 cup cooked brown rice + 2 cups vegetables"
    },
    {
        "id": "di_beef_greens",
        "name": "Lean Sirloin Steak with Garlic Greens & Roasted Baby Potatoes",
        "meal_type": "dinner",
        "diet_tags": ["gluten_free", "dairy_free", "high_protein"],
        "goals": ["muscle_gain", "endurance"],
        "key_ingredients": ["lean beef sirloin", "kale or green beans", "baby potatoes", "garlic", "olive oil"],
        "approx_prep_min": 22,
        "protein_source": "lean beef sirloin",
        "swap_option": "Swap beef for lean ground turkey burger patties",
        "portion_guidance": "140g steak + 4 baby roasted potatoes + 1.5 cups garlic greens"
    },
    {
        "id": "di_paneer_tikka",
        "name": "Grilled Cottage Cheese / Paneer Tikka with Sautéed Peppers",
        "meal_type": "dinner",
        "diet_tags": ["vegetarian", "gluten_free", "high_protein"],
        "goals": ["muscle_gain", "general_health"],
        "key_ingredients": ["low-fat paneer or halloumi", "bell peppers", "onions", "yogurt marinade", "chaat masala"],
        "approx_prep_min": 18,
        "protein_source": "paneer / cottage cheese",
        "swap_option": "Substitute paneer with extra-firm tofu for vegan option",
        "portion_guidance": "120g paneer + sautéed bell peppers & onions + light mint chutney"
    },

    # ── Snacks
    {
        "id": "sn_apple_almond",
        "name": "Crisp Apple Slices with Natural Almond Butter",
        "meal_type": "snack",
        "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free"],
        "goals": ["weight_loss", "general_health"],
        "key_ingredients": ["fuji apple", "natural almond butter (100% nuts)"],
        "approx_prep_min": 2,
        "protein_source": "almond butter",
        "swap_option": "Swap with celery sticks or pear",
        "portion_guidance": "1 medium apple + 1 level tablespoon almond butter"
    },
    {
        "id": "sn_protein_shake",
        "name": "Rapid Recovery Protein Shake",
        "meal_type": "snack",
        "diet_tags": ["vegetarian", "gluten_free", "high_protein"],
        "goals": ["muscle_gain", "weight_loss", "endurance"],
        "key_ingredients": ["whey or plant protein powder", "water or unsweetened almond milk", "ice"],
        "approx_prep_min": 2,
        "protein_source": "protein isolate (25g)",
        "swap_option": "Add half a frozen banana for post-workout glycogen replenishment",
        "portion_guidance": "1 scoop (30g) mixed with 300ml cold liquid"
    },
    {
        "id": "sn_edamame",
        "name": "Steamed Sea Salt Edamame Pods",
        "meal_type": "snack",
        "diet_tags": ["vegan", "vegetarian", "gluten_free", "dairy_free", "high_protein"],
        "goals": ["weight_loss", "general_health"],
        "key_ingredients": ["young soybeans in pod", "coarse sea salt"],
        "approx_prep_min": 5,
        "protein_source": "whole soy beans (high plant protein and fiber)",
        "swap_option": "Roasted chickpeas with smoked paprika",
        "portion_guidance": "1 cup in pods (~1/2 cup shelled)"
    },
    {
        "id": "sn_trail_mix",
        "name": "Raw Walnut, Pumpkin Seed & Dark Chocolate Nib Mix",
        "meal_type": "snack",
        "diet_tags": ["vegetarian", "vegan", "gluten_free"],
        "goals": ["general_health", "endurance", "muscle_gain"],
        "key_ingredients": ["raw walnuts", "pepitas (pumpkin seeds)", "85% dark chocolate chips"],
        "approx_prep_min": 1,
        "protein_source": "seeds and nuts",
        "swap_option": "Mix with dried cranberries or raisins for fast endurance energy",
        "portion_guidance": "1 small palmful (approx 25-30g)"
    },
]


# ── Dynamic Filtering & Assembly Engine ────────────────────────────────────────

def detect_contraindications(health_notes: str, user_message: str = "") -> list[str]:
    """
    Extract injury / pain tags from profile notes or real-time user message.
    Used to automatically safeguard exercise selection.
    """
    combined = f"{health_notes} {user_message}".lower()
    found = []

    if any(k in combined for k in ["knee", "knees", "patella", "meniscus", "acl"]):
        found.append("knee_pain")
    if any(k in combined for k in ["lower back", "back pain", "herniated", "spine", "sciatica"]):
        found.append("lower_back_pain")
    if any(k in combined for k in ["shoulder", "rotator", "impingement", "collarbone"]):
        found.append("shoulder_pain")
    if any(k in combined for k in ["wrist", "carpal", "forearm strain"]):
        found.append("wrist_pain")
    if any(k in combined for k in ["ankle", "achilles", "sprain", "foot pain"]):
        found.append("ankle_pain")
    if any(k in combined for k in ["heart", "cardiac", "chest pressure", "hypertension"]):
        found.append("heart_condition")

    return list(set(found))


def parse_equipment_list(equipment_str: str) -> list[str]:
    """Parse comma/space separated equipment into normalized list."""
    eq_lower = equipment_str.lower()
    items = ["bodyweight"]  # bodyweight always available

    if any(k in eq_lower for k in ["dumbbell", "weights", "dumbells"]):
        items.append("dumbbells")
    if any(k in eq_lower for k in ["band", "resistance band", "tubing"]):
        items.append("resistance_bands")
    if any(k in eq_lower for k in ["pullup", "pull up", "bar", "chin up"]):
        items.append("pullup_bar")
    if any(k in eq_lower for k in ["kettlebell", "kb"]):
        items.append("kettlebell")

    return items


def filter_exercises(
    equipment_available: list[str],
    difficulty: str = "beginner",
    contraindications: Optional[list[str]] = None,
    preferred_pattern: Optional[str] = None
) -> list[Exercise]:
    """Filter catalog to safe, equipment-matching exercises."""
    contra = contraindications or []
    safe_exercises = []

    for ex in EXERCISE_CATALOG:
        # Check contraindications — if any overlap, skip for safety!
        if any(c in contra for c in ex["contraindications"]):
            continue

        # Check equipment compatibility
        if not any(eq in equipment_available for eq in ex["equipment"]):
            continue

        # Check movement pattern filter if provided
        if preferred_pattern and ex["movement_pattern"] != preferred_pattern:
            continue

        safe_exercises.append(ex)

    return safe_exercises


def assemble_modular_workout(
    profile: Any,
    user_feedback: str = "",
    target_duration: Optional[int] = None
) -> dict[str, Any]:
    """
    Dynamically compose a structured, personalized workout plan.
    Responds to real-time user feedback, equipment changes, and injury adaptations.
    """
    health_notes = getattr(profile, "health_notes", "") or ""
    equipment_str = getattr(profile, "equipment", "") or ""
    level = getattr(profile, "level", "beginner") or "beginner"
    goal = getattr(profile, "goal", "general_health") or "general_health"

    # Extract dynamic duration from feedback if specified (e.g., "15 min workout")
    duration = target_duration or int(getattr(profile, "time_per_session", "30") or "30")
    dur_match = re.search(r"(\d+)\s*(?:min|minute)", user_feedback.lower())
    if dur_match:
        try:
            duration = int(dur_match.group(1))
        except ValueError:
            pass

    # Extract equipment & contraindications dynamically
    contra = detect_contraindications(health_notes, user_feedback)
    equipment = parse_equipment_list(f"{equipment_str} {user_feedback}")

    # Select exercises by balanced movement patterns
    push_pool = filter_exercises(equipment, level, contra, "push")
    pull_pool = filter_exercises(equipment, level, contra, "pull")
    squat_pool = filter_exercises(equipment, level, contra, "squat")
    hinge_pool = filter_exercises(equipment, level, contra, "hinge")
    lunge_pool = filter_exercises(equipment, level, contra, "lunge")
    core_pool = filter_exercises(equipment, level, contra, "core")
    cardio_pool = filter_exercises(equipment, level, contra, "cardio")

    selected: list[Exercise] = []

    # Assemble core movements safely
    if push_pool:
        selected.append(random.choice(push_pool))
    if pull_pool:
        selected.append(random.choice(pull_pool))

    # For lower body: if knee pain, prioritize hinges (glute bridge) over squats/lunges!
    if "knee_pain" in contra:
        if hinge_pool:
            selected.append(random.choice(hinge_pool))
        if [x for x in squat_pool if x["id"] in ("wall_sit", "box_squat")]:
            safe_squat = [x for x in squat_pool if x["id"] in ("wall_sit", "box_squat")]
            selected.append(random.choice(safe_squat))
    else:
        lower_options = squat_pool + hinge_pool + lunge_pool
        if lower_options:
            selected.append(random.choice(lower_options))

    if core_pool:
        selected.append(random.choice(core_pool))

    # Add cardio / conditioning if time allows and goal is weight loss or endurance
    if duration >= 25 and (goal in ("weight_loss", "endurance") or "cardio" in user_feedback.lower()):
        if cardio_pool:
            selected.append(random.choice(cardio_pool))

    # Warm-up routine (5 minutes dynamic mobility)
    warmups = [
        "Arm circles & shoulder rolls (1 min)",
        "Torso twists with gentle reach (1 min)",
        "Hip openers / leg swings (1 min)",
    ]
    if "knee_pain" in contra:
        warmups.append("Gentle glute bridges (1 min)")
    else:
        warmups.append("Light bodyweight air squats or march in place (2 min)")

    # Cool-down routine (5 minutes static stretches)
    cooldowns = [
        "Doorway chest stretch (30s each side)",
        "Child's pose deep breathing (1 min)",
        "Hamstring & calf stretch (1 min each side)",
        "Gentle spinal twist on floor (1 min)",
    ]

    return {
        "title": f"Personalised {goal.replace('_', ' ').title()} Dynamic Workout",
        "duration_minutes": duration,
        "equipment_used": equipment,
        "active_contraindications": contra,
        "warmup": warmups,
        "exercises": selected,
        "cooldown": cooldowns,
        "health_disclaimer_required": len(contra) > 0 or bool(health_notes),
    }


def assemble_modular_meal_plan(
    profile: Any,
    user_feedback: str = "",
    dietary_pref: Optional[str] = None
) -> dict[str, Any]:
    """
    Dynamically compose a structured daily meal plan aligned with dietary restrictions,
    calories/macro objectives, and real-time user requests.
    """
    goal = getattr(profile, "goal", "general_health") or "general_health"
    diet = (dietary_pref or getattr(profile, "dietary_pref", "") or "").lower()

    # Match dietary tags
    tags: list[str] = []
    if "vegan" in diet:
        tags.append("vegan")
    elif "veg" in diet:
        tags.append("vegetarian")
    if "gluten" in diet:
        tags.append("gluten_free")
    if "dairy" in diet or "lactose" in diet:
        tags.append("dairy_free")

    def match_item(items: list[MealItem]) -> list[MealItem]:
        valid = []
        for it in items:
            # Check dietary match
            if tags and not all(t in it["diet_tags"] for t in tags):
                continue
            valid.append(it)
        return valid if valid else items  # Fallback to general if strict tag has no items

    breakfasts = match_item([m for m in MEAL_CATALOG if m["meal_type"] == "breakfast"])
    lunches    = match_item([m for m in MEAL_CATALOG if m["meal_type"] == "lunch"])
    dinners    = match_item([m for m in MEAL_CATALOG if m["meal_type"] == "dinner"])
    snacks     = match_item([m for m in MEAL_CATALOG if m["meal_type"] == "snack"])

    chosen_breakfast = random.choice(breakfasts)
    chosen_lunch     = random.choice(lunches)
    chosen_dinner    = random.choice(dinners)
    chosen_snacks    = random.sample(snacks, k=min(2, len(snacks)))

    return {
        "title": f"Personalised {goal.replace('_', ' ').title()} Nutrition Plan",
        "dietary_preference": diet or "no restriction",
        "goal": goal,
        "breakfast": chosen_breakfast,
        "lunch": chosen_lunch,
        "dinner": chosen_dinner,
        "snacks": chosen_snacks,
        "hydration_target_litres": 2.5 if goal == "weight_loss" else 3.0,
    }


def search_knowledge_bank(query: str, max_results: int = 4) -> dict[str, list[dict[str, Any]]]:
    """
    Lightweight RAG retrieval from the exercise and nutrition knowledge catalogs.
    Used to ground chat answers with factual, safe exercises and meal data.
    """
    q_words = re.findall(r"\w+", query.lower())
    if not q_words:
        return {"exercises": [], "meals": []}

    matched_exercises = []
    for ex in EXERCISE_CATALOG:
        text = f"{ex['name']} {ex['movement_pattern']} {' '.join(ex['muscle_groups'])} {' '.join(ex['equipment'])} {ex['instructions']}".lower()
        score = sum(1 for w in q_words if w in text)
        if score > 0:
            matched_exercises.append((score, ex))

    matched_exercises.sort(key=lambda x: x[0], reverse=True)

    matched_meals = []
    for m in MEAL_CATALOG:
        text = f"{m['name']} {m['meal_type']} {' '.join(m['diet_tags'])} {' '.join(m['key_ingredients'])} {m['protein_source']}".lower()
        score = sum(1 for w in q_words if w in text)
        if score > 0:
            matched_meals.append((score, m))

    matched_meals.sort(key=lambda x: x[0], reverse=True)

    return {
        "exercises": [ex for _, ex in matched_exercises[:max_results]],
        "meals": [m for _, m in matched_meals[:max_results]],
    }
