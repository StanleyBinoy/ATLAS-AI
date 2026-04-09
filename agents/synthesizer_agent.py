# This module defines the synthesizer agent that merges swarm outputs into the final answer.
from agents.base_agent import BaseAgent


class SynthesizerAgent(BaseAgent):
    def __init__(self):
        """Initialize the synthesizer agent with its role description."""
        super().__init__(
            "Synthesizer",
            "You combine planner notes, research notes, execution details, and tool findings into one final user-facing answer only. Avoid duplication, mention degraded mode if live web search failed, and include sources only when provided.",
        )
