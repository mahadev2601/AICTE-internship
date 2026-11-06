"""
app.py — Flask web server for Fitness Buddy chatbot.

Endpoints:
  GET  /                        → serves static/index.html
  POST /api/onboard             → saves profile to disk, returns personalised welcome
  GET  /api/profile/<name>      → load a saved profile by name (login)
  GET  /api/profile             → returns current session profile as JSON
  POST /api/chat                → processes a message, returns personalised AI response
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
import agent.prompts as prompts
from agent.model import generate

app = Flask(__name__, static_folder="static")
CORS(app)

_agent = FitnessBuddy()

# ── Profile persistence ───────────────────────────────────────────────────────
# Use /tmp on cloud platforms (ephemeral but survives the session),
# or the project directory locally.
_PROFILES_FILE = os.path.join(
    os.getenv("PROFILES_DIR", os.path.dirname(os.path.abspath(__file__))),
    "profiles.json"
)


def _load_all_profiles() -> dict:
    """Load all saved profiles from disk. Returns {} on first run."""
    if os.path.exists(_PROFILES_FILE):
        try:
            with open(_PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_profile(profile: UserProfile) -> None:
    """Persist a profile keyed by lowercased name."""
    profiles = _load_all_profiles()
    profiles[profile.name.lower().strip()] = profile.to_dict()
    with open(_PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)

# ── Intent routing ────────────────────────────────────────────────────────────
_INTENT_KEYWORDS = {
    "workout":    ["workout", "exercise", "training", "gym", "routine", "fitness plan", "work out"],
    "meal":       ["meal", "food", "eat", "nutrition", "diet", "breakfast", "lunch", "dinner", "snack", "recipe"],
    "motivation": ["motivat", "inspire", "quote", "encourage", "mood", "energy boost", "feeling low"],
    "habit":      ["habit", "routine", "consistency", "tip", "daily", "schedule", "discipline"],
    "checkin":    ["check-in", "checkin", "progress", "weekly", "report", "how did i do", "my week"],
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
        "model":  "ibm/granite-4-h-small" if _agent.model else "offline",
        "online": _agent.model is not None,
    })


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Return the current session profile."""
    return jsonify(_agent.profile.to_dict())


@app.route("/api/profile/<name>", methods=["GET"])
def load_profile(name: str):
    """
    Load a previously saved profile by name.
    Called on page load when localStorage has a saved name.
    Returns the profile and a returning-user greeting.
    """
    profiles = _load_all_profiles()
    data = profiles.get(name.lower().strip())
    if not data:
        return jsonify({"found": False}), 404

    _agent.profile = UserProfile.from_dict(data)
    p = _agent.profile

    # Generate a brief returning-user greeting (non-blocking; short)
    system = prompts.SYSTEM
    user_msg = (
        f"{prompts._profile_context(p)}\n\n"
        f"Write a warm 1-sentence welcome-back message for {p.name} who has returned "
        f"to Fitness Buddy. Reference their {p.goal.replace('_',' ')} goal. Be encouraging."
    )
    fallback = (
        f"Welcome back, {p.name}! Ready to keep pushing towards your "
        f"{p.goal.replace('_', ' ')} goal? Let's go! 💪"
    )
    greeting = generate(_agent.model, system, user_msg, fallback)
    return jsonify({"found": True, "profile": p.to_dict(), "greeting": greeting})


@app.route("/api/onboard", methods=["POST"])
def onboard():
    """
    Accept full user profile, save it to disk, generate a personalised welcome.
    Called once from the web onboarding wizard.
    """
    data = request.get_json(force=True, silent=True) or {}
    _agent.profile = UserProfile.from_dict(data)
    _save_profile(_agent.profile)          # ← persist to profiles.json

    p = _agent.profile
    system, user_msg = prompts.onboarding_summary(p)
    fallback = (
        f"Welcome, {p.name}! I've built your personalised plan around your "
        f"{p.goal.replace('_', ' ')} goal and {p.level} level. "
        f"With {p.days_per_week} days/week and {p.time_per_session} minutes per session, "
        f"you're ready to go — let's crush your goals!"
    )
    welcome = generate(_agent.model, system, user_msg, fallback)
    return jsonify({"welcome": welcome, "profile": p.to_dict()})


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Allow inline profile updates from chat (e.g. if user edits their profile)
    profile_fields = {k: v for k, v in data.items()
                      if k in UserProfile.__dataclass_fields__ and k != "message"}
    if profile_fields:
        for k, v in profile_fields.items():
            setattr(_agent.profile, k, v)
        _save_profile(_agent.profile)      # persist any profile changes

    intent   = _detect_intent(message)
    response = ""

    if intent == "workout":
        response = _agent.show_workout()
    elif intent == "meal":
        response = _agent.show_meal_plan()
    elif intent == "motivation":
        response = _agent.show_motivation()
    elif intent == "habit":
        response = _agent.show_habit_tips()
    elif intent == "checkin":
        # Check-in via API returns AI feedback directly without stdin prompts
        workouts = data.get("workouts", "unknown")
        water    = data.get("water",    "unknown")
        sleep    = data.get("sleep",    _agent.profile.sleep_hours)
        energy   = data.get("energy",   "5")
        p = _agent.profile
        system, user_msg = prompts.progress_feedback(p, workouts, water, sleep, energy)
        fallback = (
            f"Great effort this week, {p.name}! "
            f"Keep pushing towards your {p.days_per_week} workout target. "
            f"Consistency is your greatest asset."
        )
        response = generate(_agent.model, system, user_msg, fallback)
    else:
        response = _agent.ask_question(message)

    return jsonify({
        "response": response.strip(),
        "intent":   intent,
    })


# ── Image analysis ────────────────────────────────────────────────────────────
# Image types the agent can interpret
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
    If a vision model is available, passes the image directly.
    Falls back to text-only analysis using the caption + image type.
    """
    import warnings
    p = _agent.profile

    # Accept multipart/form-data
    image_type   = request.form.get("image_type", "other")
    user_caption = request.form.get("caption", "").strip()
    image_file   = request.files.get("image")

    if not image_file:
        return jsonify({"error": "No image file provided"}), 400

    # Read and base64-encode the image
    img_bytes = image_file.read()
    img_b64   = base64.b64encode(img_bytes).decode()
    mime_type = image_file.content_type or "image/jpeg"

    system, user_msg = _build_image_prompt(p, image_type, user_caption)

    # Try vision API first (if model supports it)
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
            vision_response = None  # fall through to text-only

    if not vision_response:
        # Text-only fallback: describe what we know from image_type + caption
        fallback_user = (
            f"{_profile_context(p)}\n\n"
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
        from agent.model import generate
        vision_response = generate(
            _agent.model, system, fallback_user,
            f"## 🔍 Image Received\n\nThank you for uploading your {image_type} image, {p.name}! "
            f"For a detailed analysis, please describe what you see — I'll give you specific advice "
            f"tailored to your {p.goal.replace('_',' ')} goal right away."
        )

    return jsonify({
        "response": vision_response,
        "intent":   "image",
    })


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n  Fitness Buddy web server  →  http://localhost:{port}")
    print(f"  Model: {'ibm/granite-4-h-small' if _agent.model else 'offline mode'}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
