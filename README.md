# Fitness Buddy — AI Health & Fitness Coach

> **AICTE Internship — Problem Statement No. 13**  
> Powered by IBM Granite via watsonx.ai, Flask, SQLite, and an intelligent modular agent architecture.

---

## 🚀 Architectural Overview & Upgrades

This project addresses and resolves the 4 primary architectural drawbacks of conversational fitness AI agents:

### 1. Dynamic & Modular Recommendations (Replaces Static Hardcoding)
- **Problem**: Fixed static files (`workout_plans.py`, `meal_plans.py`) prevented true personalization based on real-time feedback, injuries, or available equipment.
- **Solution**:
  - Implemented `data/knowledge_bank.py` containing a modular, categorized library of 40+ exercises and complete nutrition components with rich metadata (muscle groups, movement patterns, equipment, difficulty, and injury contraindications).
  - Exercises and meals are dynamically assembled via `assemble_modular_workout()` and `assemble_modular_meal_plan()`, adapting to user constraints (e.g., knee pain, lower back discomfort, 15-minute quick sessions, dumbbell-only routines).
  - Prompt templates feed the LLM structured schemas, allowing dynamic expansion while grounding against hallucinations.

### 2. Scalable State Management & Progressive Overload Tracking (Replaces Flat JSON)
- **Problem**: Storing user data in `profiles.json` was vulnerable to concurrent write corruption, lacked historical progress tracking, and did not track progressive overload.
- **Solution**:
  - Migrated to an ACID-compliant, thread-safe SQLite database (`data/database.py`) with WAL mode.
  - Automatically migrates existing profiles from legacy `profiles.json` on startup.
  - Added dedicated tables for `users`, `workout_logs`, `progressive_overload`, `checkins`, `chat_history`, and `conversation_summaries`.
  - Added progressive overload calculation: automatically tracks personal bests, previous weights/reps lifted, and calculates recommended targets for the next session.

### 3. Safety, Moderation & Medical Liability Guardrails
- **Problem**: Sensitive health topics carry liability risks if an AI hallucinates medical advice, clinical diagnoses, or exercises that exacerbate injuries.
- **Solution**:
  - Implemented `agent/guardrails.py` (`SafetyGuard`):
    - **Acute Emergency Interception**: Detects red-flag symptoms (chest pain, shortness of breath, severe dizziness, acute fractures) and immediately halts exercise, directing the user to emergency medical care.
    - **Clinical Scope Boundaries**: Politely declines clinical disease diagnoses, physical therapy prescriptions, and anabolic steroids/prescription medications.
    - **Injury Safeguards**: Automatically identifies conditions like knee or back pain and excludes contraindicated exercises.
    - **Mandatory Medical Disclaimers**: Enforces clinical disclaimers on all health, workout, and nutrition outputs.

### 4. Intelligent Context Window Management & RAG Engine
- **Problem**: Passing unbounded conversation history and complete user profiles to the LLM overflows context windows, degrades response quality, and increases API costs.
- **Solution**:
  - Implemented `agent/context_manager.py` (`ContextManager`):
    - **Sliding Window Memory**: Maintains the last 4–6 conversation turns within token limits.
    - **Rolling Memory Summarization**: Periodically condenses older conversation turns into a dense 2–3 sentence memory summary.
    - **RAG Telemetry Retrieval**: Selectively injects only relevant fitness data (recent progressive overload benchmarks, recent logs, check-ins, or semantic knowledge bank items) based on query intent.

---

## 📁 Project Structure

```
AICTE-internship/
├── agent/
│   ├── fitness_agent.py      # Main FitnessBuddy conversational agent
│   ├── context_manager.py    # Sliding window memory, RAG retrieval & summarization
│   ├── guardrails.py         # Moderation, emergency interception & medical disclaimers
│   ├── model.py              # IBM Granite (watsonx.ai) chat wrapper & fallback
│   ├── prompts.py            # Dynamic prompt templates with structured schemas
│   └── __init__.py
├── data/
│   ├── database.py           # SQLite database layer & migration engine
│   ├── knowledge_bank.py     # Modular exercise & nutrition catalog (40+ exercises)
│   ├── meal_plans.py         # Dynamic meal plan interface (backward-compatible)
│   ├── quotes.py             # Curated motivational quotes and habit tips
│   ├── workout_plans.py      # Dynamic workout interface (backward-compatible)
│   └── __init__.py
├── static/
│   └── index.html            # Glassmorphism & Neumorphism web interface with PDF export
├── tests/
│   └── test_fitness_buddy.py # Automated test suite (17 tests covering all upgrades)
├── app.py                    # Flask REST API server
├── main.py                   # Interactive CLI interface
├── config.py                 # Centralised configuration & environment variables
├── requirements.txt          # Python dependencies
└── wsgi.py                   # Production WSGI entry point
```

---

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mahadev2601/AICTE-internship.git
   cd AICTE-internship
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables (Optional for IBM Granite cloud access):**
   Copy `.env.example` to `.env` and fill in your IBM watsonx.ai credentials:
   ```bash
   WATSONX_API_KEY=your_ibm_cloud_api_key
   WATSONX_PROJECT_ID=your_project_id
   WATSONX_URL=https://us-south.ml.cloud.ibm.com
   ```
   *(If credentials are not set, Fitness Buddy operates seamlessly in offline mode using the dynamic modular knowledge bank).*

---

## 🏃 Running the Application

### Web Application (Flask + Glassmorphism UI)
```bash
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

### CLI Application (Interactive Terminal)
```bash
python main.py
```

### Running Tests
```bash
python -m unittest tests/test_fitness_buddy.py -v
```