"""
agent/context_manager.py — Intelligent Context Management & RAG Engine.

Prevents context window bloat and reduces token costs:
1. Maintains a rolling sliding window of recent conversation turns.
2. Periodically summarizes older conversation history into compact memory anchors.
3. Retrieves only the fitness data relevant to the current query (recent progressive
   overload records, check-in stats, and exercise/nutrition knowledge).
"""

from __future__ import annotations

import logging
from typing import Optional, Any
from data.database import db
from data.knowledge_bank import search_knowledge_bank
from config import MAX_CHAT_HISTORY_TURNS

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages token-budgeted prompt context, RAG retrieval, and conversation memory."""

    def __init__(self, database=None) -> None:
        self.db = database or db

    def get_sliding_window_history(self, user_name: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Fetch the most recent turns within the token budget."""
        n_turns = limit or MAX_CHAT_HISTORY_TURNS
        return self.db.get_recent_chat_history(user_name, limit=n_turns)

    def retrieve_relevant_fitness_context(
        self,
        profile: Any,
        intent: str,
        query: str = ""
    ) -> str:
        """
        RAG Retrieval: selectively pull only the data points relevant to the current task.
        Avoids dumping irrelevant logs into the prompt.
        """
        user_name = getattr(profile, "name", "Champion")
        sections: list[str] = []

        # 1. Rolling memory summary (if exists)
        summary = self.db.get_conversation_summary(user_name)
        if summary:
            sections.append(f"**Past Context Summary:** {summary}")

        # 2. Intent-specific RAG retrieval
        if intent in ("workout", "checkin", "freeform"):
            # Fetch progressive overload records for current exercises
            overload = self.db.get_progressive_overload_summary(user_name)
            if overload:
                top_benchmarks = [
                    f"- {item['exercise']}: Last {item['last_weight_kg']}kg × {item['last_reps']} reps (Target: {item['recommended_target']})"
                    for item in overload[:3]
                ]
                sections.append("**Progressive Overload Benchmarks:**\n" + "\n".join(top_benchmarks))

            # Fetch recent workout history
            recent_workouts = self.db.get_recent_workouts(user_name, limit=3)
            if recent_workouts:
                recent_logs = [
                    f"- {w['logged_at'][:10]}: {w['exercise_name']} ({w['sets']} sets × {w['reps']} reps @ {w['weight_kg']}kg)"
                    for w in recent_workouts
                ]
                sections.append("**Recent Workout Logs:**\n" + "\n".join(recent_logs))

        if intent in ("checkin", "habit"):
            # Fetch last check-in stats
            past_checkins = self.db.get_checkin_history(user_name, limit=1)
            if past_checkins:
                last_chk = past_checkins[0]
                sections.append(
                    f"**Last Week's Check-in:** {last_chk['workouts_completed']}/{last_chk['target_workouts']} workouts completed, "
                    f"Sleep: {last_chk['sleep_hours']}h, Energy: {last_chk['energy_level']}/10."
                )

        if intent in ("freeform", "workout", "meal") and query:
            # Semantic search in knowledge bank
            kb_results = search_knowledge_bank(query, max_results=2)
            kb_snippets = []
            if kb_results.get("exercises"):
                for ex in kb_results["exercises"]:
                    kb_snippets.append(f"- Exercise '{ex['name']}': {ex['instructions']} (Cue: {ex['cues']})")
            if kb_results.get("meals"):
                for m in kb_results["meals"]:
                    kb_snippets.append(f"- Nutrition '{m['name']}': {m['portion_guidance']} (Prep: {m['approx_prep_min']}m)")
            if kb_snippets:
                sections.append("**Knowledge Bank Grounding:**\n" + "\n".join(kb_snippets))

        return "\n\n".join(sections)

    def build_concise_profile_snapshot(self, profile: Any) -> str:
        """
        Generate a tight, token-budgeted profile string.
        Only includes essential attributes.
        """
        p = profile
        return (
            f"**Client Profile:** {p.name} | Goal: {p.goal.replace('_', ' ').title()} | "
            f"Level: {p.level.title()} | Schedule: {p.days_per_week}d/wk ({p.time_per_session}min/session) | "
            f"Equipment: {p.equipment or 'Bodyweight only'} | Diet: {p.dietary_pref or 'None'} | "
            f"Health: {p.health_notes or 'None'}"
        )

    def update_conversation_summary(
        self,
        user_name: str,
        model: Optional[object] = None
    ) -> None:
        """
        Periodically compress older conversation history into a concise rolling summary.
        Keeps context small and prevents memory loss across long sessions.
        """
        total_msgs = self.db.get_chat_message_count(user_name)
        if total_msgs < 6:
            return  # No need to summarize very short conversations

        recent = self.db.get_recent_chat_history(user_name, limit=10)
        if not recent:
            return

        last_id = recent[-1].get("id", 0)

        # Build transcript of turns to condense
        transcript = "\n".join(
            f"{turn['role'].capitalize()}: {turn['message'][:150]}"
            for turn in recent
        )

        existing_summary = self.db.get_conversation_summary(user_name) or "None"

        # If model is available, use it to synthesize a dense 2-sentence summary
        if model:
            from agent.model import generate
            system = "You are a concise fitness memory compressor. Output only 2-3 short factual bullet points."
            user_msg = (
                f"Previous summary: {existing_summary}\n\n"
                f"Recent messages:\n{transcript}\n\n"
                f"Summarize the client's current fitness progress, key preferences, injuries mentioned, and ongoing focus."
            )
            fallback = (
                f"User actively following plan. Prefers {recent[-1]['intent']} focus. "
                f"Logged recent consistency."
            )
            dense_summary = generate(model, system, user_msg, fallback)
        else:
            # Rule-based fallback summary
            dense_summary = (
                f"User {user_name} has completed {total_msgs} interactions. "
                f"Recent focus: {recent[-1]['intent']}. Active tracking enabled."
            )

        self.db.save_conversation_summary(user_name, dense_summary.strip(), last_id)
        logger.info("Updated rolling memory summary for user '%s'.", user_name)


# Global singleton instance
context_mgr = ContextManager()
