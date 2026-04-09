# This module runs the ATLAS console application and coordinates the multi-agent workflow.
import config
from agents.swarm_orchestrator import SwarmOrchestrator
from memory.chroma_store import clear_memory, is_memory_available, save_memory
from tools.task_logger import print_task_history
from ui.console import (
    print_agent_response,
    print_banner,
    print_error,
    print_success,
    print_thinking,
    prompt_user,
)


def print_startup_status():
    """Print the current ATLAS startup configuration and service status."""
    active_model = "OpenRouter" if config.OPENROUTER_API_KEY else "Ollama"
    chroma_status = "connected" if is_memory_available() else "not found"
    print("ATLAS version: 1.0.0")
    print(f"Active model: {active_model}")
    print(f"ChromaDB status: {chroma_status}")
    print(f"SQLite log path: {config.SQLITE_DB_PATH}")


def main():
    """Start the interactive ATLAS console loop."""
    _ = config
    orchestrator = SwarmOrchestrator()

    print_banner()
    print("ATLAS is starting up...")
    print_startup_status()

    while True:
        user_input = prompt_user("What do you want ATLAS to do? (type 'exit' to quit)")
        command = user_input.strip().lower()

        if command == "exit":
            print("Shutting down ATLAS. Goodbye.")
            break

        if command == "help":
            print("Available commands:")
            print('help - list available commands')
            print('history - show recent tasks')
            print('clear memory - wipe ChromaDB memory')
            print('exit - quit ATLAS')
            continue

        if command == "history":
            print_task_history()
            continue

        if command == "clear memory":
            clear_memory()
            continue

        swarm_result = orchestrator.run_swarm_task(
            user_input,
            status_callback=print_thinking,
            output_callback=print_agent_response,
        )
        result = swarm_result["final_answer"]
        print_agent_response("ATLAS", result)

        exchange = swarm_result["exchange"]
        feedback = prompt_user("Was this response helpful? (y/n/skip): ")

        if feedback.strip().lower() == "y":
            save_memory(exchange, metadata={"feedback": "positive"})
            print_success("Saved positive feedback to memory.")
        elif feedback.strip().lower() == "n":
            critique = prompt_user("What was wrong?")
            save_memory(
                f"{exchange}\n\nUser critique: {critique}",
                metadata={"feedback": "negative", "critique": critique},
            )
            print_success("Saved negative feedback and critique to memory.")
        elif feedback.strip().lower() != "skip":
            print_error("Unknown feedback option. Skipping memory feedback save.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down ATLAS. Goodbye.")
