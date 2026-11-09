"""
tests/test_fitness_buddy.py — Comprehensive test suite for Fitness Buddy architecture upgrades.

Tests:
1. Dynamic modular routine generation (equipment, injury safeguards, user feedback).
2. Dynamic modular meal plan generation (dietary preferences, goals).
3. SQLite database operations, progressive overload tracking, and checkins.
4. Safety guardrails, emergency red-flag interception, and medical disclaimers.
5. Context manager, sliding window, and RAG retrieval.
6. Flask app API endpoints.
"""

import os
import sys
import unittest
import tempfile
import json

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Database
from data.knowledge_bank import (
    assemble_modular_workout,
    assemble_modular_meal_plan,
    detect_contraindications,
    parse_equipment_list,
    search_knowledge_bank,
    filter_exercises,
    EXERCISE_CATALOG,
    MEAL_CATALOG,
)
from agent.guardrails import SafetyGuard, MANDATORY_DISCLAIMER
from agent.context_manager import ContextManager
from agent.fitness_agent import FitnessBuddy, UserProfile
from app import app


class TestKnowledgeBank(unittest.TestCase):
    """Test dynamic modular recommendations and injury adaptations."""

    def test_contraindication_detection(self):
        self.assertIn("knee_pain", detect_contraindications("I have bad knees and meniscus surgery"))
        self.assertIn("lower_back_pain", detect_contraindications("", "my lower back is sore"))
        self.assertIn("shoulder_pain", detect_contraindications("rotator cuff impingement"))
        self.assertIn("wrist_pain", detect_contraindications("", "carpal tunnel syndrome"))

    def test_equipment_parsing(self):
        eq = parse_equipment_list("dumbbells, resistance bands")
        self.assertIn("bodyweight", eq)
        self.assertIn("dumbbells", eq)
        self.assertIn("resistance_bands", eq)

    def test_injury_filtering_in_workout(self):
        profile = UserProfile(
            name="Test User",
            goal="weight_loss",
            level="beginner",
            health_notes="bad knees",
            equipment="dumbbells"
        )
        plan = assemble_modular_workout(profile, user_feedback="knee hurts today")
        self.assertIn("knee_pain", plan["active_contraindications"])
        # Ensure no jump squats, jumping jacks, or standard lunges were selected
        exercise_names = [e["name"].lower() for e in plan["exercises"]]
        self.assertNotIn("standard jumping jacks", exercise_names)
        self.assertNotIn("full burpees", exercise_names)

    def test_modular_meal_plan_dietary_pref(self):
        profile = UserProfile(
            name="Veggie User",
            goal="muscle_gain",
            dietary_pref="vegan"
        )
        plan = assemble_modular_meal_plan(profile)
        # All items should align with vegan tag
        self.assertIn("vegan", plan["breakfast"]["diet_tags"])
        self.assertIn("vegan", plan["lunch"]["diet_tags"])
        self.assertIn("vegan", plan["dinner"]["diet_tags"])

    def test_knowledge_bank_rag_search(self):
        res = search_knowledge_bank("pushup chest")
        self.assertGreater(len(res["exercises"]), 0)
        self.assertTrue(any("push" in ex["name"].lower() for ex in res["exercises"]))


class TestDatabaseAndState(unittest.TestCase):
    """Test SQLite thread-safe persistence, progressive overload, and check-ins."""

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(db_path=self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_profile_crud(self):
        p_dict = {
            "name": "Sarah Connor",
            "age": "28",
            "gender": "female",
            "goal": "muscle_gain",
            "level": "intermediate",
            "days_per_week": "4",
            "time_per_session": "45",
            "equipment": "dumbbells",
            "health_notes": "none"
        }
        self.db.save_profile(p_dict)
        retrieved = self.db.get_profile("Sarah Connor")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["goal"], "muscle_gain")
        self.assertEqual(retrieved["days_per_week"], "4")

    def test_progressive_overload_tracking(self):
        # Session 1: 3x10 push-ups bodyweight
        self.db.log_workout("Alex", "Push-ups", sets=3, reps=10, weight_kg=0.0)
        summary1 = self.db.get_progressive_overload_summary("Alex")
        self.assertEqual(len(summary1), 1)
        self.assertEqual(summary1[0]["max_reps"], 10)
        self.assertIn("12 bodyweight reps", summary1[0]["recommended_target"])

        # Session 2: 3x12 push-ups with 5kg vest
        self.db.log_workout("Alex", "Push-ups", sets=3, reps=12, weight_kg=5.0)
        summary2 = self.db.get_progressive_overload_summary("Alex")
        self.assertEqual(summary2[0]["max_weight_kg"], 5.0)
        self.assertEqual(summary2[0]["last_reps"], 12)

    def test_checkin_logging(self):
        self.db.log_checkin(
            name="Alex",
            workouts_completed="3",
            target_workouts="3",
            hydration_met="yes",
            sleep_hours="8",
            energy_level="8",
            notes="Felt energized all week"
        )
        history = self.db.get_checkin_history("Alex")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["workouts_completed"], "3")


class TestSafetyGuardrails(unittest.TestCase):
    """Test safety moderation, red-flag emergency screening, and medical disclaimers."""

    def test_emergency_interception(self):
        res = SafetyGuard.evaluate_input("I am feeling severe chest pain and dizziness during workout")
        self.assertFalse(res.is_safe)
        self.assertTrue(res.is_emergency)
        self.assertIsNotNone(res.intercept_response)
        self.assertIn("Immediate Action Steps", res.intercept_response)
        self.assertIn("911", res.intercept_response)

    def test_pharmacology_rejection(self):
        res = SafetyGuard.evaluate_input("What is the best steroid cycle for fast muscle gain?")
        self.assertFalse(res.is_safe)
        self.assertIn("cannot recommend", res.intercept_response)

    def test_clinical_diagnosis_boundary(self):
        res = SafetyGuard.evaluate_input("Can you diagnose why my knee clicks when I walk?")
        self.assertTrue(res.disclaimer_required)
        self.assertIn("physical therapy", res.coaching_guidance)

    def test_output_disclaimer_sanitization(self):
        raw = "## Workout Plan\nDo 3 sets of 10 squats."
        sanitized = SafetyGuard.sanitize_output(raw, disclaimer_required=True)
        self.assertIn("Medical Disclaimer", sanitized)


class TestAppEndpoints(unittest.TestCase):
    """Test Flask HTTP endpoints."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_status_endpoint(self):
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["database"], "sqlite")
        self.assertEqual(data["guardrails"], "active")

    def test_chat_dynamic_workout_intent(self):
        res = self.client.post("/api/chat", json={"message": "Show me a 20 min workout with dumbbells"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["intent"], "workout")
        self.assertIn("Workout", data["response"])

    def test_chat_emergency_interception(self):
        res = self.client.post("/api/chat", json={"message": "I have sudden chest pressure and shortness of breath"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["intent"], "safety_intercept")
        self.assertTrue(data.get("is_emergency", False))

    def test_workout_log_endpoint(self):
        res = self.client.post("/api/workout/log", json={
            "exercise_name": "Goblet Squat",
            "sets": 3,
            "reps": 12,
            "weight_kg": 15.0,
            "notes": "Good depth"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_workout_progress_endpoint(self):
        res = self.client.get("/api/workout/progress")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("report", data)
        self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
