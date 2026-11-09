"""
main.py — CLI Entry point for Fitness Buddy.

Interactive command-line interface featuring:
- Dynamic modular workout & meal plan generation
- Progressive overload logging and tracking
- Safety guardrail protection & medical disclaimers
- Conversational fitness Q&A with memory
"""

import sys
from agent.fitness_agent import FitnessBuddy


_MENU = """
╔══════════════════════════════════════════════════════════════╗
║                 FITNESS BUDDY — MAIN MENU                    ║
╠══════════════════════════════════════════════════════════════╣
║  1  ->  Get my dynamic workout plan                          ║
║  2  ->  Customize workout (e.g. 20 min, knee pain, dumbells) ║
║  3  ->  Show me a personalised meal plan                     ║
║  4  ->  Log a completed workout set (Progressive Overload)   ║
║  5  ->  View my Progressive Overload Tracker                 ║
║  6  ->  Daily motivation                                     ║
║  7  ->  Habit-building tips                                  ║
║  8  ->  Ask a fitness/nutrition question                     ║
║  9  ->  Weekly progress check-in                             ║
║  0  ->  Exit                                                 ║
╚══════════════════════════════════════════════════════════════╝
"""


def main() -> None:
    agent = FitnessBuddy()
    print(agent.greet())

    # If profile exists in database, ask if returning user
    p = agent.profile
    if p and p.name != "Champion":
        print(f"  Recognised profile: '{p.name}' ({p.goal.replace('_',' ')}, {p.level})")
        change = input("  Continue with this profile? (y/n, default 'y'): ").strip().lower()
        if change == "n":
            agent.collect_profile()
    else:
        agent.collect_profile()

    while True:
        print(_MENU)
        choice = input("  Your choice (0-9): ").strip()

        if choice == "1":
            print("\n" + agent.show_workout() + "\n")

        elif choice == "2":
            feedback = input("\n  Enter adjustments (e.g. '15 minutes, dumbbells only, knee-friendly'): ").strip()
            print("\n" + agent.show_workout(user_feedback=feedback) + "\n")

        elif choice == "3":
            diet_feedback = input("\n  Any dietary preferences/adjustments? (Press Enter to keep profile): ").strip()
            print("\n" + agent.show_meal_plan(user_feedback=diet_feedback) + "\n")

        elif choice == "4":
            print("\n  LOG WORKOUT SET:")
            ex_name = input("  Exercise name (e.g. Push-ups, Squats) : ").strip()
            if ex_name:
                sets = int(input("  Sets completed (default 3)            : ").strip() or "3")
                reps = int(input("  Reps completed per set (default 10)   : ").strip() or "10")
                weight = float(input("  Weight in kg (0 for bodyweight)       : ").strip() or "0")
                notes = input("  Notes / how it felt (optional)        : ").strip()
                result = agent.log_workout_set(ex_name, sets, reps, weight_kg=weight, notes=notes)
                print(f"\n  {result}\n")

        elif choice == "5":
            print("\n" + agent.get_progressive_overload_report() + "\n")

        elif choice == "6":
            print("\n" + agent.show_motivation() + "\n")

        elif choice == "7":
            print("\n" + agent.show_habit_tips() + "\n")

        elif choice == "8":
            question = input("\n  Your question: ").strip()
            if question:
                print(f"\n{agent.ask_question(question)}\n")

        elif choice == "9":
            print("\n" + agent.progress_checkin() + "\n")

        elif choice == "0":
            user_name = agent.profile.name
            print(f"\n  See you next time, {user_name}! Stay consistent and keep moving!\n")
            sys.exit(0)

        else:
            print("  Invalid option — please enter a number between 0 and 9.")

        input("  Press Enter to return to menu...")


if __name__ == "__main__":
    main()
