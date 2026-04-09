# This module defines the executor agent used to carry out plans step by step.
from agents.base_agent import BaseAgent


class ExecutorAgent(BaseAgent):
    def __init__(self):
        """Initialize the executor agent with its role description."""
        super().__init__(
            "Executor",
            "You turn plan and research context into a concrete answer draft. Do not narrate actions, do not role-play execution, and do not claim live browsing unless sources are provided.",
        )
