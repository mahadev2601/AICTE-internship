"""
app.py — Flask web server for Fitness Buddy chatbot.

Endpoints:
  GET  /                        → serves static/index.html
  POST /api/onboard             → saves profile to SQLite DB, returns personalised welcome
  GET  /api/profile/<name>      → load a saved profile by name (login)
  GET  /api/profile             → returns current session profile as JSON
  POST /api/chat                → processes a message with guardrails & conversational memory
  POST /api/workout/log         → logs completed exercise sets & updates progressive overload
  GET  /api/workout/progress    → returns progressive overload benchmarks and workout history
  GET  /api/checkins            → returns historical check-in data
  GET  /api/chat/history        → returns recent conversation turns & rolling memory summary
  POST /api/image               → analyses an uploaded image
  GET  /api/status              → returns model status (online/offline)
"""

import os
import sys
import json
import base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

from agent.fitness_agent import FitnessBuddy, UserProfile
from data.database import db
import agent.prompts as prompts
from agent.model import generate
from agent.guardrails import SafetyGuard

app = Flask(__name__, static_folder="static")
CORS(app)

_agent = FitnessBuddy(database=db)


# ── Profile persistence (SQLite-backed) ───────────────────────────────────────

def _load_all_profiles() -> dict:
    """Load all saved profiles from database."""
    return db.list_all_profiles()


def _save_profile(profile: UserProfile) -> None:
    """Persist a profile to database."""
    _agent.set_profile(profile)


# ── Intent routing ────────────────────────────────────────────────────────────
_INTENT_KEYWORDS = {
    "workout":    ["workout", "exercise", "training", "gym", "routine", "fitness plan", "work out"],
    "meal":       ["meal", "food", "eat", "nutrition", "diet", "breakfast", "lunch", "dinner", "snack", "recipe"],
    "motivation": ["motivat", "inspire", "quote", "encourage", "mood", "energy boost", "feeling low"],
    "habit":      ["habit", "routine", "consistency", "tip", "daily", "schedule", "discipline"],
    "checkin":    ["check-in", "checkin", "weekly report", "how did i do", "my week"],
    "progress":   ["progressive overload", "my progress", "personal record", "pr", "weights lifted"],
}


def _detect_intent(message: str) -> str:
    msg = message.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return intent
    return "freeform"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def status():
    return jsonify({
        "model":  "ibm/granite-4-h-small" if _agent.model else "offline (dynamic engine)",
        "online": _agent.model is not None,
        "database": "sqlite",
        "guardrails": "active",
        "rag": "active",
    })


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Return the current session profile."""
    return jsonify(_agent.profile.to_dict())


@app.route("/api/profile/<name>", methods=["GET"])
def load_profile(name: str):
    """
    Load a previously saved profile by name from SQLite database.
    Called on page load when localStorage has a saved name.
    """
    found = _agent.load_profile_by_name(name)
    if not found:
        return jsonify({"found": False}), 404

    p = _agent.profile

    # Generate a brief returning-user greeting
    system = prompts.SYSTEM
    user_msg = (
        f"{prompts._profile_context(p)}\n\n"
        f"Write a warm 1-sentence welcome-back message for {p.name} who has returned "
        f"to Fitness Buddy. Reference their {p.goal.replace('_',' ')} goal and encourage them."
    )
    fallback = (
        f"Welcome back, {p.name}! Ready to keep pushing towards your "
        f"{p.goal.replace('_', ' ')} goal? Let's crush today's session! 💪"
    )
    greeting = generate(_agent.model, system, user_msg, fallback)
    return jsonify({"found": True, "profile": p.to_dict(), "greeting": greeting})


@app.route("/api/onboard", methods=["POST"])
def onboard():
    """
    Accept full user profile, save it to SQLite database, and generate a personalised welcome.
    """
    data = request.get_json(force=True, silent=True) or {}
    new_profile = UserProfile.from_dict(data)
    _agent.set_profile(new_profile)

    p = _agent.profile
    system, user_msg = prompts.onboarding_summary(p)
    fallback = (
        f"Welcome, {p.name}! I've built your dynamic plan around your "
        f"{p.goal.replace('_', ' ')} goal and {p.level} level. "
        f"With {p.days_per_week} days/week and {p.time_per_session} minutes per session, "
        f"you're all set — let's crush your goals!"
    )
    welcome = generate(_agent.model, system, user_msg, fallback)
    return jsonify({"welcome": welcome, "profile": p.to_dict()})


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Chat endpoint with moderation guardrails, dynamic modular generation,
    and conversational memory.
    """
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Allow inline profile updates from chat
    profile_fields = {k: v for k, v in data.items()
                      if k in UserProfile.__dataclass_fields__ and k != "message"}
    if profile_fields:
        for k, v in profile_fields.items():
            setattr(_agent.profile, k, v)
        _agent.set_profile(_agent.profile)

    # 1. Moderation & Safety Screen
    guard_res = SafetyGuard.evaluate_input(message, _agent.profile)
    if not guard_res.is_safe and guard_res.intercept_response:
        db.save_chat_message(_agent.profile.name, "user", message, "safety_intercept")
        db.save_chat_message(_agent.profile.name, "assistant", guard_res.intercept_response, "safety_intercept")
        return jsonify({
            "response": guard_res.intercept_response,
            "intent": "safety_intercept",
            "is_emergency": guard_res.is_emergency
        })

    intent = _detect_intent(message)
    response = ""

    if intent == "workout":
        # Pass real-time user message into modular workout generator!
        response = _agent.show_workout(user_feedback=message)
        db.save_chat_message(_agent.profile.name, "user", message, intent)
        db.save_chat_message(_agent.profile.name, "assistant", response, intent)
    elif intent == "meal":
        # Pass real-time user message into modular meal generator!
        response = _agent.show_meal_plan(user_feedback=message)
        db.save_chat_message(_agent.profile.name, "user", message, intent)
        db.save_chat_message(_agent.profile.name, "assistant", response, intent)
    elif intent == "motivation":
        response = _agent.show_motivation()
        db.save_chat_message(_agent.profile.name, "user", message, intent)
        db.save_chat_message(_agent.profile.name, "assistant", response, intent)
    elif intent == "habit":
        response = _agent.show_habit_tips()
        db.save_chat_message(_agent.profile.name, "user", message, intent)
        db.save_chat_message(_agent.profile.name, "assistant", response, intent)
    elif intent == "progress":
        response = _agent.get_progressive_overload_report()
        db.save_chat_message(_agent.profile.name, "user", message, intent)
        db.save_chat_message(_agent.profile.name, "assistant", response, intent)
    elif intent == "checkin":
        workouts = str(data.get("workouts", "unknown"))
        water    = str(data.get("water",    "unknown"))
        sleep    = str(data.get("sleep",    _agent.profile.sleep_hours))
        energy   = str(data.get("energy",   "5"))
        response = _agent.progress_checkin(workouts=workouts, water=water, sleep=sleep, energy=energy)
        db.save_chat_message(_agent.profile.name, "user", f"Check-in: {workouts} workouts, {sleep}h sleep, {energy}/10 energy", intent)
        db.save_chat_message(_agent.profile.name, "assistant", response, intent)
    else:
        # Free-form Q&A with RAG & conversation memory
        response = _agent.ask_question(message)

    return jsonify({
        "response": response.strip(),
        "intent":   intent,
    })


# ── Workout Logging & Progressive Overload Endpoints ─────────────────────────

@app.route("/api/workout/log", methods=["POST"])
def log_workout():
    """
    Log a completed workout set and update progressive overload benchmarks.
    Body JSON: { exercise_name: str, sets: int, reps: int, weight_kg?: float, rpe?: int, notes?: str }
    """
    data = request.get_json(force=True, silent=True) or {}
    exercise = (data.get("exercise_name") or data.get("exercise") or "").strip()
    if not exercise:
        return jsonify({"error": "No exercise name provided"}), 400

    try:
        sets = int(data.get("sets", 3))
        reps = int(data.get("reps", 10))
        weight = float(data.get("weight_kg", 0.0))
        duration = int(data.get("duration_sec", 0))
        rpe = int(data.get("rpe", 7))
        notes = str(data.get("notes", ""))
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid parameter format: {exc}"}), 400

    msg = _agent.log_workout_set(exercise, sets, reps, weight, duration, rpe, notes)
    return jsonify({"success": True, "message": msg})


@app.route("/api/workout/progress", methods=["GET"])
def workout_progress():
    """Return progressive overload summary, PRs, and recent workout logs."""
    report = _agent.get_progressive_overload_report()
    summary = db.get_progressive_overload_summary(_agent.profile.name)
    recent = db.get_recent_workouts(_agent.profile.name, limit=10)
    return jsonify({
        "report": report,
        "summary": summary,
        "recent": recent
    })


@app.route("/api/checkins", methods=["GET"])
def checkin_history():
    """Retrieve historical weekly check-in records."""
    history = db.get_checkin_history(_agent.profile.name, limit=10)
    return jsonify({"history": history})


@app.route("/api/chat/history", methods=["GET"])
def chat_history():
    """Retrieve recent conversation history and rolling memory summary."""
    turns = db.get_recent_chat_history(_agent.profile.name, limit=20)
    summary = db.get_conversation_summary(_agent.profile.name)
    return jsonify({"history": turns, "summary": summary})


# ── Image analysis ────────────────────────────────────────────────────────────

_IMAGE_CONTEXTS = {
    "food":    "Analyse this food/meal image for a fitness client.",
    "posture": "Analyse this exercise posture or body position image.",
    "body":    "Analyse this body composition or progress photo.",
    "label":   "Analyse this nutrition label or food packaging.",
    "other":   "Analyse this image in the context of health and fitness.",
}


def _build_image_prompt(p, image_type: str, user_caption: str) -> tuple[str, str]:
    """Build a grounded image-analysis prompt using the user's profile."""
    from agent.prompts import SYSTEM, _profile_context
    context = _IMAGE_CONTEXTS.get(image_type, _IMAGE_CONTEXTS["other"])
    user_msg = (
        f"{_profile_context(p)}\n\n"
        f"Image type: {image_type}\n"
        f"User caption / question: {user_caption or 'Please analyse this image.'}\n\n"
        f"{context} Provide a **specific, professional analysis** in Markdown:\n\n"
        f"## 🔍 Image Analysis\n"
        f"What you observe that is relevant to {p.name}'s {p.goal.replace('_',' ')} goal.\n\n"
        f"## ✅ What Looks Good\n"
        f"Specific positives based on what is visible.\n\n"
        f"## 💡 Recommendations for {p.name}\n"
        f"2-3 specific, actionable suggestions aligned with their profile.\n\n"
        f"Do NOT invent calorie counts, diagnose injuries, or make medical claims. "
        f"If the image is unclear, say so honestly."
    )
    return SYSTEM, user_msg


@app.route("/api/image", methods=["POST"])
def analyse_image():
    """
    Accept an uploaded image + optional caption and image type.
    Passes to vision model if available; falls back to text-only analysis.
    """
    import warnings
    p = _agent.profile

    image_type   = request.form.get("image_type", "other")
    user_caption = request.form.get("caption", "").strip()
    image_file   = request.files.get("image")

    if not image_file:
        return jsonify({"error": "No image file provided"}), 400

    img_bytes = image_file.read()
    img_b64   = base64.b64encode(img_bytes).decode()
    mime_type = image_file.content_type or "image/jpeg"

    system, user_msg = _build_image_prompt(p, image_type, user_caption)

    vision_response = None
    if _agent.model:
        try:
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text",      "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{img_b64}"}},
                ]
            }]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = _agent.model.chat(  # type: ignore[union-attr]
                    messages=[{"role": "system", "content": system}] + messages,
                    params={"max_tokens": 600, "temperature": 0.3}
                )
            vision_response = raw["choices"][0]["message"]["content"].strip()
        except Exception:
            vision_response = None

    if not vision_response:
        fallback_user = (
            f"{prompts._profile_context(p)}\n\n"
            f"The user has uploaded a {image_type} image with the caption: "
            f"'{user_caption or 'no caption provided'}'.\n\n"
            f"Without seeing the image directly, provide **general professional advice** "
            f"in Markdown based on the image type and the user's profile:\n\n"
            f"## 🔍 Based on Your {image_type.title()} Image\n"
            f"General guidance for someone with {p.name}'s goals when analysing a {image_type} image.\n\n"
            f"## 💡 Recommendations for {p.name}\n"
            f"3 specific, actionable tips aligned with their {p.goal.replace('_',' ')} goal.\n\n"
            f"## ℹ️ Note\n"
            f"For precise analysis, please describe what you see in the image as text."
        )
        vision_response = generate(
            _agent.model, system, fallback_user,
            f"## 🔍 Image Received\n\nThank you for uploading your {image_type} image, {p.name}! "
            f"For a detailed analysis, please describe what you see — I'll give you specific advice "
            f"tailored to your {p.goal.replace('_',' ')} goal right away."
        )

    clean_vision = SafetyGuard.sanitize_output(vision_response, disclaimer_required=True)
    return jsonify({
        "response": clean_vision,
        "intent":   "image",
    })


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n  Fitness Buddy web server  →  http://localhost:{port}")
    print(f"  Model: {'ibm/granite-4-h-small' if _agent.model else 'offline mode (dynamic modular engine)'}")
    print(f"  Database: SQLite ({db.db_path})\n")
    app.run(host="0.0.0.0", port=port, debug=False)
