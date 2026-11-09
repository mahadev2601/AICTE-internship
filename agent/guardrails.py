"""
agent/guardrails.py — Comprehensive safety, moderation, and liability guardrails.

Protects against hallucinations, unsafe exercise prescriptions, and medical liability.
Provides input screening for medical red flags/acute emergencies, clinical boundary
enforcement (politely declining physical therapy or medical diagnosis), and output
sanitization with mandatory medical disclaimers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Any


MANDATORY_DISCLAIMER = (
    "\n\n> ⚠️ **Medical Disclaimer**: Fitness Buddy is an AI fitness companion designed for educational "
    "and wellness guidance only. It does not provide clinical medical advice, diagnosis, or physical therapy. "
    "Always consult a physician or certified healthcare provider before starting any new exercise routine "
    "or nutrition program, especially if you experience pain or have pre-existing health conditions."
)


@dataclass
class GuardrailResult:
    """Outcome of safety evaluation on user query."""
    is_safe: bool = True
    is_emergency: bool = False
    intercept_response: Optional[str] = None
    detected_conditions: list[str] = field(default_factory=list)
    disclaimer_required: bool = False
    coaching_guidance: str = ""


class SafetyGuard:
    """Moderation layer enforcing fitness-only scope and liability safety."""

    # Emergency symptoms requiring immediate clinical referral
    EMERGENCY_PATTERNS = [
        r"\b(?:chest pain|chest pressure|heart attack|angina)\b",
        r"\b(?:shortness of breath|can't breathe|cannot breathe|struggling to breathe)\b",
        r"\b(?:faint|fainted|blacked out|loss of consciousness|severe dizziness)\b",
        r"\b(?:coughing up blood|vomiting blood|sudden numbness)\b",
        r"\b(?:broke|broken bone|fracture|bone poking|severely dislocated)\b",
        r"\b(?:anorexia|bulimia|starving myself|laxative abuse)\b",
    ]

    # Clinical pharmacology / prescription drugs out of scope
    PHARMA_PATTERNS = [
        r"\b(?:steroid cycle|anabolic steroids|trenbolone|dianabol|winstrol|clenbuterol)\b",
        r"\b(?:ozempic|wegovy|semaglutide|tirzepatide|saxenda)\b",
        r"\b(?:insulin dose|prescription medication|antibiotic|adderall)\b",
    ]

    # Requests for clinical diagnosis or physical therapy rehabilitation
    CLINICAL_DIAGNOSIS_PATTERNS = [
        r"\b(?:diagnose|do i have|what illness|what disease|is this cancer)\b",
        r"\b(?:physical therapy protocol|rehab my torn|rehabilitate (?:torn|ruptured))\b",
        r"\b(?:cure my (?:diabetes|hypertension|kidney|liver))\b",
    ]

    # Common non-emergency injuries and conditions requiring caution
    CONDITION_KEYWORDS = {
        "knee_pain": ["knee", "patella", "meniscus", "acl", "knee pain"],
        "lower_back_pain": ["lower back", "lumbar", "sciatica", "slipped disc", "herniated disc", "back ache"],
        "shoulder_pain": ["shoulder", "rotator cuff", "impingement", "frozen shoulder", "shoulder pain"],
        "wrist_pain": ["wrist", "carpal tunnel", "wrist pain"],
        "hypertension": ["high blood pressure", "hypertension", "bp is high"],
        "diabetes": ["diabetes", "diabetic", "blood sugar"],
        "asthma": ["asthma", "inhaler", "wheezing"],
        "pregnancy": ["pregnant", "pregnancy", "postpartum"],
    }

    @classmethod
    def evaluate_input(cls, message: str, profile: Optional[Any] = None) -> GuardrailResult:
        """
        Screen user input against emergency red flags, clinical pharmacology,
        and requests for clinical diagnosis.
        """
        msg_lower = message.lower().strip()
        result = GuardrailResult()

        # Check Emergency Symptoms
        for pat in cls.EMERGENCY_PATTERNS:
            if re.search(pat, msg_lower):
                result.is_safe = False
                result.is_emergency = True
                result.intercept_response = (
                    "## 🚨 Important Health & Safety Notice\n\n"
                    "The symptoms you described (such as chest pain, severe shortness of breath, "
                    "fainting, or suspected acute fractures) are medical red flags that require "
                    "**immediate professional medical evaluation**.\n\n"
                    "### ⚠️ Immediate Action Steps:\n"
                    "- **Stop all physical exercise immediately**.\n"
                    "- If you are experiencing chest pain, difficulty breathing, or severe trauma, "
                    "call your local emergency services (e.g., **911**, **112**, or your local emergency line) "
                    "or have someone take you to the nearest Emergency Room.\n"
                    "- Fitness Buddy cannot provide medical diagnosis or treatment for acute health conditions.\n\n"
                    "Please prioritize your immediate health and safety with a licensed medical professional."
                )
                result.disclaimer_required = True
                return result

        # Check Pharmacology / Steroids / Prescription Injections
        for pat in cls.PHARMA_PATTERNS:
            if re.search(pat, msg_lower):
                result.is_safe = False
                result.intercept_response = (
                    "## 💊 Clinical Prescription & Substance Guidance\n\n"
                    "As an AI fitness and nutrition coach, I cannot recommend, endorse, or calculate dosages "
                    "for anabolic steroids, prescription hormones, or regulated pharmacological weight-loss medications.\n\n"
                    "### 💡 Safe & Evidence-Based Alternative:\n"
                    "- Focus on progressive resistance training, adequate dietary protein, and restorative sleep.\n"
                    "- Any use of prescription medications must be monitored exclusively by a licensed physician or endocrinologist.\n"
                    + MANDATORY_DISCLAIMER
                )
                result.disclaimer_required = True
                return result

        # Check Requests for Medical Diagnosis or Clinical Rehabilitation
        for pat in cls.CLINICAL_DIAGNOSIS_PATTERNS:
            if re.search(pat, msg_lower):
                result.is_safe = True  # Allowed to respond, but with clinical refusal boundary
                result.disclaimer_required = True
                result.coaching_guidance = (
                    "The user is asking for a clinical diagnosis or medical treatment. "
                    "You MUST politely state that as an AI fitness buddy you cannot clinically diagnose conditions "
                    "or prescribe physical therapy rehabilitation. Recommend they consult a licensed doctor or physical therapist. "
                    "Offer only safe, general non-clinical mobility advice."
                )

        # Detect non-emergency conditions & injuries from message + profile
        combined_text = msg_lower
        if profile and hasattr(profile, "health_notes") and profile.health_notes:
            combined_text += " " + profile.health_notes.lower()

        detected = []
        for cond_key, keywords in cls.CONDITION_KEYWORDS.items():
            if any(kw in combined_text for kw in keywords):
                detected.append(cond_key)

        result.detected_conditions = detected
        if detected:
            result.disclaimer_required = True

        return result

    @classmethod
    def sanitize_output(cls, output: str, disclaimer_required: bool = False) -> str:
        """
        Verify that output contains no fabricated dangerous advice and
        ensure mandatory medical disclaimer is appended when health issues are involved.
        """
        cleaned = output.strip()

        # Check if already has disclaimer
        has_disclaimer = any(
            phrase in cleaned.lower()
            for phrase in ["medical disclaimer", "consult a physician", "consult a doctor", "qualified healthcare"]
        )

        if disclaimer_required and not has_disclaimer:
            cleaned += MANDATORY_DISCLAIMER

        return cleaned
