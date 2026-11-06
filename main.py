"""
main.py — Entry point for Fitness Buddy.

Runs the interactive CLI loop. Import and UI logic is kept here;
all business logic lives in the agent and data packages.
"""

from agent.fitness_agent import FitnessBuddy


_MENU = """
╔══════════════════════════════════════════════╗
║        WHAT WOULD YOU LIKE TODAY?            ║
╠══════════════════════════════════════════════╣
║  1  ->  Get my workout plan                  ║
║  2  ->  Show me a meal plan                  ║
║  3  ->  Daily motivation                     ║
║  4  ->  Habit-building tips                  ║
║  5  ->  Ask a fitness/nutrition question     ║
║  6  ->  Weekly progress check-in             ║
║  7  ->  Exit                                 ║
╚══════════════════════════════════════════════╝
"""


def main() -> None:
    agent = FitnessBuddy()
    print(agent.greet())
    agent.collect_profile()

    while True:
        print(_MENU)
        choice = input("  Your choice: ").strip()

        if choice == "1":
            print(agent.show_workout())

        elif choice == "2":
            print(agent.show_meal_plan())

        elif choice == "3":
            print(agent.show_motivation())

        elif choice == "4":
            print(agent.show_habit_tips())

        elif choice == "5":
            question = input("\n  Your question: ").strip()
            if question:
                print(f"\n  Fitness Buddy:\n  {agent.ask_question(question)}\n")

        elif choice == "6":
            print(agent.progress_checkin())

        elif choice == "7":
            name = agent._profile().name
            print(f"\n  See you next time, {name}! Stay consistent and keep moving!\n")
            break

        else:
            print("  Invalid option — please enter a number between 1 and 7.")

        input("\n  Press Enter to continue...")


if __name__ == "__main__":
    main()
