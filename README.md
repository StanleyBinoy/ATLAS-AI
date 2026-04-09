# ATLAS

ATLAS - A local multi-agent AI system that thinks, remembers, and improves.

## What it does

ATLAS is a Python-based local AI system built around a simple multi-agent pipeline:

- `Planner` breaks a user request into clear steps.
- `Researcher` gathers supporting context and reasoning.
- `Executor` produces the final response.

ATLAS also includes:

- ChromaDB memory for storing past conversations and useful examples
- SQLite task logging for tracking what the system has done
- Self-improvement through RAG-style feedback, where positively rated responses can be reused as guidance for future tasks

## Requirements

- Python 3.10+
- Ollama installed locally
- Optional OpenRouter API key

## Quick Start

```bash
git clone [repo]
cd atlas
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Then add your OpenRouter key to `.env`.

## Project Structure

```text
atlas
|   .env.example
|   .gitignore
|   config.py
|   CONTRIBUTING.md
|   main.py
|   README.md
|   requirements.txt
|
+---agents
|       base_agent.py
|       executor_agent.py
|       manager_agent.py
|       model_connector.py
|       planner_agent.py
|       researcher_agent.py
|       swarm_orchestrator.py
|       synthesizer_agent.py
|       web_research_agent.py
|       __init__.py
|
+---memory
|       chroma_store.py
|       __init__.py
|
+---tools
|       task_logger.py
|       web_search.py
|       __init__.py
|
\---ui
        console.py
        __init__.py
```

## Contributing

Each module (`agents/`, `memory/`, `tools/`) is self-contained. Pick a folder and improve it. Open a PR with what you changed and why.

## Roadmap

- Web UI
- Voice input
- More specialist agents
- Auto-task scheduling
