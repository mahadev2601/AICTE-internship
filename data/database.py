"""
data/database.py — Scalable SQLite database layer for Fitness Buddy.

Replaces flat JSON storage with an ACID-compliant, thread-safe SQLite database.
Provides schema management, automatic migration from legacy profiles.json,
progressive overload tracking, check-in history, and conversational memory.
"""

from __future__ import annotations

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Any
from contextlib import contextmanager

from config import DATABASE_PATH, PROFILES_FILE

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe SQLite database manager for user state and fitness telemetry."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DATABASE_PATH
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()
        self._migrate_legacy_profiles()

    @contextmanager
    def _get_connection(self):
        """Context manager providing a SQLite connection with WAL mode and row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables for profiles, workouts, progressive overload, checkins, and chat history."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    name_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age TEXT DEFAULT 'unknown',
                    gender TEXT DEFAULT 'prefer not to say',
                    height TEXT DEFAULT 'not provided',
                    weight TEXT DEFAULT 'not provided',
                    goal TEXT DEFAULT 'general_health',
                    level TEXT DEFAULT 'beginner',
                    days_per_week TEXT DEFAULT '3',
                    time_per_session TEXT DEFAULT '30',
                    equipment TEXT DEFAULT '',
                    dietary_pref TEXT DEFAULT '',
                    health_notes TEXT DEFAULT '',
                    sleep_hours TEXT DEFAULT '7',
                    stress_level TEXT DEFAULT '5',
                    motivation_style TEXT DEFAULT 'encouragement',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workout_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_key TEXT NOT NULL,
                    exercise_name TEXT NOT NULL,
                    sets INTEGER NOT NULL DEFAULT 3,
                    reps INTEGER NOT NULL DEFAULT 10,
                    weight_kg REAL NOT NULL DEFAULT 0.0,
                    duration_sec INTEGER DEFAULT 0,
                    rpe INTEGER DEFAULT 7,
                    notes TEXT DEFAULT '',
                    logged_at TEXT NOT NULL,
                    FOREIGN KEY (user_key) REFERENCES users (name_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS progressive_overload (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_key TEXT NOT NULL,
                    exercise_name TEXT NOT NULL,
                    max_weight_kg REAL NOT NULL DEFAULT 0.0,
                    max_reps INTEGER NOT NULL DEFAULT 0,
                    last_weight_kg REAL NOT NULL DEFAULT 0.0,
                    last_reps INTEGER NOT NULL DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    UNIQUE(user_key, exercise_name),
                    FOREIGN KEY (user_key) REFERENCES users (name_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_key TEXT NOT NULL,
                    workouts_completed TEXT DEFAULT '0',
                    target_workouts TEXT DEFAULT '3',
                    hydration_met TEXT DEFAULT 'unknown',
                    sleep_hours TEXT DEFAULT '7',
                    energy_level TEXT DEFAULT '5',
                    notes TEXT DEFAULT '',
                    ai_feedback TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_key) REFERENCES users (name_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_key TEXT NOT NULL,
                    session_id TEXT DEFAULT 'default',
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    intent TEXT DEFAULT 'freeform',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_key) REFERENCES users (name_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    user_key TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    last_message_id INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_key) REFERENCES users (name_key) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_workout_user ON workout_logs (user_key, logged_at);
                CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history (user_key, timestamp);
            """)
        logger.info("Database schema initialised at %s", self.db_path)

    def _migrate_legacy_profiles(self) -> None:
        """Migrate existing profiles from profiles.json if present and not already in database."""
        if not os.path.exists(PROFILES_FILE):
            return
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                for key, p in data.items():
                    name_key = key.strip().lower()
                    existing = conn.execute("SELECT name_key FROM users WHERE name_key = ?", (name_key,)).fetchone()
                    if not existing:
                        conn.execute("""
                            INSERT INTO users (
                                name_key, name, age, gender, height, weight, goal, level,
                                days_per_week, time_per_session, equipment, dietary_pref,
                                health_notes, sleep_hours, stress_level, motivation_style,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            name_key,
                            p.get("name", "Champion"),
                            str(p.get("age", "unknown")),
                            str(p.get("gender", "prefer not to say")),
                            str(p.get("height", "not provided")),
                            str(p.get("weight", "not provided")),
                            str(p.get("goal", "general_health")),
                            str(p.get("level", "beginner")),
                            str(p.get("days_per_week", "3")),
                            str(p.get("time_per_session", "30")),
                            str(p.get("equipment", "")),
                            str(p.get("dietary_pref", "")),
                            str(p.get("health_notes", "")),
                            str(p.get("sleep_hours", "7")),
                            str(p.get("stress_level", "5")),
                            str(p.get("motivation_style", "encouragement")),
                            now, now
                        ))
                        logger.info("Migrated profile '%s' from profiles.json to database.", name_key)
        except Exception as exc:
            logger.warning("Could not migrate legacy profiles.json: %s", exc)

    # ── User Profile Operations ───────────────────────────────────────────────

    def save_profile(self, profile_dict: dict[str, Any]) -> None:
        """Insert or update a user profile. Keyed by lowercased name."""
        name = profile_dict.get("name", "Champion").strip()
        name_key = name.lower()
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO users (
                    name_key, name, age, gender, height, weight, goal, level,
                    days_per_week, time_per_session, equipment, dietary_pref,
                    health_notes, sleep_hours, stress_level, motivation_style,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name_key) DO UPDATE SET
                    name = excluded.name,
                    age = excluded.age,
                    gender = excluded.gender,
                    height = excluded.height,
                    weight = excluded.weight,
                    goal = excluded.goal,
                    level = excluded.level,
                    days_per_week = excluded.days_per_week,
                    time_per_session = excluded.time_per_session,
                    equipment = excluded.equipment,
                    dietary_pref = excluded.dietary_pref,
                    health_notes = excluded.health_notes,
                    sleep_hours = excluded.sleep_hours,
                    stress_level = excluded.stress_level,
                    motivation_style = excluded.motivation_style,
                    updated_at = excluded.updated_at
            """, (
                name_key,
                name,
                str(profile_dict.get("age", "unknown")),
                str(profile_dict.get("gender", "prefer not to say")),
                str(profile_dict.get("height", "not provided")),
                str(profile_dict.get("weight", "not provided")),
                str(profile_dict.get("goal", "general_health")),
                str(profile_dict.get("level", "beginner")),
                str(profile_dict.get("days_per_week", "3")),
                str(profile_dict.get("time_per_session", "30")),
                str(profile_dict.get("equipment", "")),
                str(profile_dict.get("dietary_pref", "")),
                str(profile_dict.get("health_notes", "")),
                str(profile_dict.get("sleep_hours", "7")),
                str(profile_dict.get("stress_level", "5")),
                str(profile_dict.get("motivation_style", "encouragement")),
                now, now
            ))

        # Mirror to profiles.json for backward compatibility with external scripts
        self._sync_to_profiles_json()

    def get_profile(self, name: str) -> Optional[dict[str, Any]]:
        """Retrieve a profile by name (case-insensitive)."""
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE name_key = ?", (name_key,)).fetchone()
            if not row:
                return None
            return {
                "name": row["name"],
                "age": row["age"],
                "gender": row["gender"],
                "height": row["height"],
                "weight": row["weight"],
                "goal": row["goal"],
                "level": row["level"],
                "days_per_week": row["days_per_week"],
                "time_per_session": row["time_per_session"],
                "equipment": row["equipment"],
                "dietary_pref": row["dietary_pref"],
                "health_notes": row["health_notes"],
                "sleep_hours": row["sleep_hours"],
                "stress_level": row["stress_level"],
                "motivation_style": row["motivation_style"],
            }

    def list_all_profiles(self) -> dict[str, dict[str, Any]]:
        """Return all user profiles keyed by lowercased name."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM users").fetchall()
            return {
                row["name_key"]: {
                    "name": row["name"],
                    "age": row["age"],
                    "gender": row["gender"],
                    "height": row["height"],
                    "weight": row["weight"],
                    "goal": row["goal"],
                    "level": row["level"],
                    "days_per_week": row["days_per_week"],
                    "time_per_session": row["time_per_session"],
                    "equipment": row["equipment"],
                    "dietary_pref": row["dietary_pref"],
                    "health_notes": row["health_notes"],
                    "sleep_hours": row["sleep_hours"],
                    "stress_level": row["stress_level"],
                    "motivation_style": row["motivation_style"],
                }
                for row in rows
            }

    def _sync_to_profiles_json(self) -> None:
        """Lightweight export of database profiles to profiles.json for backwards compatibility."""
        try:
            profiles = self.list_all_profiles()
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2)
        except Exception as exc:
            logger.warning("Could not mirror database to profiles.json: %s", exc)

    def _ensure_user_exists(self, conn: sqlite3.Connection, name: str) -> str:
        """Ensure a user record exists in the users table to prevent FK constraint failures."""
        name_key = name.strip().lower()
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT OR IGNORE INTO users (name_key, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (name_key, name.strip(), now, now))
        return name_key

    # ── Workout Logging & Progressive Overload ────────────────────────────────

    def log_workout(
        self,
        name: str,
        exercise_name: str,
        sets: int,
        reps: int,
        weight_kg: float = 0.0,
        duration_sec: int = 0,
        rpe: int = 7,
        notes: str = ""
    ) -> int:
        """
        Record a completed workout set and automatically update progressive overload targets.
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            name_key = self._ensure_user_exists(conn, name)
            # 1. Insert log entry
            cur = conn.execute("""
                INSERT INTO workout_logs (
                    user_key, exercise_name, sets, reps, weight_kg, duration_sec, rpe, notes, logged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name_key, exercise_name.strip(), sets, reps, weight_kg, duration_sec, rpe, notes, now))

            log_id = cur.lastrowid

            # 2. Update progressive overload table
            existing = conn.execute("""
                SELECT max_weight_kg, max_reps FROM progressive_overload
                WHERE user_key = ? AND exercise_name = ?
            """, (name_key, exercise_name.strip())).fetchone()

            if existing:
                new_max_weight = max(existing["max_weight_kg"], weight_kg)
                new_max_reps = max(existing["max_reps"], reps)
                conn.execute("""
                    UPDATE progressive_overload
                    SET max_weight_kg = ?, max_reps = ?, last_weight_kg = ?, last_reps = ?, last_updated = ?
                    WHERE user_key = ? AND exercise_name = ?
                """, (new_max_weight, new_max_reps, weight_kg, reps, now, name_key, exercise_name.strip()))
            else:
                conn.execute("""
                    INSERT INTO progressive_overload (
                        user_key, exercise_name, max_weight_kg, max_reps, last_weight_kg, last_reps, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name_key, exercise_name.strip(), weight_kg, reps, weight_kg, reps, now))

        return log_id

    def get_recent_workouts(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch user's recent workout log entries."""
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT exercise_name, sets, reps, weight_kg, duration_sec, rpe, notes, logged_at
                FROM workout_logs
                WHERE user_key = ?
                ORDER BY logged_at DESC
                LIMIT ?
            """, (name_key, limit)).fetchall()
            return [dict(row) for row in rows]

    def get_progressive_overload_summary(self, name: str) -> list[dict[str, Any]]:
        """
        Fetch personal records and progressive overload recommendations.
        Returns a list of exercises with previous benchmarks and targets for the next workout.
        """
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT exercise_name, max_weight_kg, max_reps, last_weight_kg, last_reps, last_updated
                FROM progressive_overload
                WHERE user_key = ?
                ORDER BY last_updated DESC
            """, (name_key,)).fetchall()

            results = []
            for r in rows:
                last_wt = r["last_weight_kg"]
                last_rp = r["last_reps"]
                # Suggest progressive overload: +1-2 reps or +1-2.5kg
                if last_wt > 0:
                    next_target = f"{last_wt + 1.25:.1f} kg × {last_rp} reps or {last_wt} kg × {last_rp + 2} reps"
                else:
                    next_target = f"{last_rp + 2} bodyweight reps or +1 set"

                results.append({
                    "exercise": r["exercise_name"],
                    "max_weight_kg": r["max_weight_kg"],
                    "max_reps": r["max_reps"],
                    "last_weight_kg": last_wt,
                    "last_reps": last_rp,
                    "last_updated": r["last_updated"],
                    "recommended_target": next_target,
                })
            return results

    # ── Check-ins ─────────────────────────────────────────────────────────────

    def log_checkin(
        self,
        name: str,
        workouts_completed: str,
        target_workouts: str,
        hydration_met: str,
        sleep_hours: str,
        energy_level: str,
        notes: str = "",
        ai_feedback: str = ""
    ) -> int:
        """Record a weekly check-in."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            name_key = self._ensure_user_exists(conn, name)
            cur = conn.execute("""
                INSERT INTO checkins (
                    user_key, workouts_completed, target_workouts, hydration_met,
                    sleep_hours, energy_level, notes, ai_feedback, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name_key, workouts_completed, target_workouts, hydration_met,
                sleep_hours, energy_level, notes, ai_feedback, now
            ))
            return cur.lastrowid

    def get_checkin_history(self, name: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve previous check-ins for the user."""
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT workouts_completed, target_workouts, hydration_met,
                       sleep_hours, energy_level, notes, ai_feedback, created_at
                FROM checkins
                WHERE user_key = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (name_key, limit)).fetchall()
            return [dict(row) for row in rows]

    # ── Conversational Memory ─────────────────────────────────────────────────

    def save_chat_message(
        self,
        name: str,
        role: str,
        message: str,
        intent: str = "freeform",
        session_id: str = "default"
    ) -> int:
        """Record a chat interaction in history."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            name_key = self._ensure_user_exists(conn, name)
            cur = conn.execute("""
                INSERT INTO chat_history (
                    user_key, session_id, role, message, intent, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (name_key, session_id, role, message, intent, now))

            return cur.lastrowid

    def get_recent_chat_history(self, name: str, limit: int = 6) -> list[dict[str, Any]]:
        """Fetch the most recent N messages for conversational memory."""
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, role, message, intent, timestamp
                FROM chat_history
                WHERE user_key = ?
                ORDER BY id DESC
                LIMIT ?
            """, (name_key, limit)).fetchall()
            # Reverse so chronological order (oldest to newest)
            return [dict(r) for r in reversed(rows)]

    def get_chat_message_count(self, name: str) -> int:
        """Count total messages for this user."""
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM chat_history WHERE user_key = ?", (name_key,)).fetchone()
            return row["cnt"] if row else 0

    def get_conversation_summary(self, name: str) -> Optional[str]:
        """Fetch the saved conversation memory summary."""
        name_key = name.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT summary FROM conversation_summaries WHERE user_key = ?", (name_key,)
            ).fetchone()
            return row["summary"] if row else None

    def save_conversation_summary(self, name: str, summary: str, last_message_id: int) -> None:
        """Save or update the concise rolling memory summary."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            name_key = self._ensure_user_exists(conn, name)
            conn.execute("""
                INSERT INTO conversation_summaries (user_key, summary, last_message_id, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_key) DO UPDATE SET
                    summary = excluded.summary,
                    last_message_id = excluded.last_message_id,
                    updated_at = excluded.updated_at
            """, (name_key, summary, last_message_id, now))



# Global singleton instance
db = Database()
