# This module defines the researcher agent that gathers supporting context and facts.
from agents.base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    def __init__(self):
        """Initialize the researcher agent with its role description."""
        super().__init__(
            "Researcher",
            "You gather evidence-based notes to answer questions. Output concise research notes only, do not pretend to browse the internet, and do not include a final user-facing answer.",
        )
