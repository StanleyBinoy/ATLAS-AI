# Contributing to ATLAS

Thanks for helping improve ATLAS.

## Repo organization

- `agents/` contains the swarm agents and model connection logic
- `memory/` contains ChromaDB memory and learning helpers
- `tools/` contains utilities such as task logging and web search helpers
- `ui/` contains console input and output helpers
- `main.py` is the entry point that connects everything together
- `config.py` stores environment-based settings and local paths

## Run locally

Before contributing, make sure the project runs on your machine:

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

If you want cloud model access, add your OpenRouter API key to `.env`. Ollama can be used locally as a fallback.

## PR rule

Each pull request should touch only one module: `agents`, `memory`, `tools`, or `ui`.

## Adding a new agent

To add a new agent:

1. Copy an existing file from `agents/`
2. Change the class name, displayed name, and role description
3. Add the new agent to `main.py`

## Suggesting new features

Open a GitHub Issue first and describe the idea before building a larger feature.

## Code style

- Write plain, readable Python
- Add comments on every function
- Avoid unnecessary dependencies
