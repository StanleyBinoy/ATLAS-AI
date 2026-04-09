# This module defines the web research agent that turns live web findings into usable notes.
from agents.base_agent import BaseAgent


class WebResearchAgent(BaseAgent):
    def __init__(self):
        """Initialize the web research agent with its role description."""
        super().__init__(
            "WebResearcher",
            "You analyze provided live web findings only, extract the most relevant facts, and present concise notes with source URLs. Do not invent sources or claim browsing beyond the provided inputs.",
        )
