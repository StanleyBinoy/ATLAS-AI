# This module defines the planner agent that breaks requests into actionable steps.
from agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    def __init__(self):
        """Initialize the planner agent with its role description."""
        super().__init__(
            "Planner",
            "You break down complex user requests into clear numbered steps. Output only the step list, nothing else.",
        )
