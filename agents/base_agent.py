# This module defines the shared parent class used by all ATLAS agents.
import json
import re

from agents.model_connector import call_model
from memory.chroma_store import get_positive_examples


class BaseAgent:
    def __init__(self, name, role_description):
        """Store the agent name and role description."""
        self.name = name
        self.role_description = role_description

    @property
    def system_prompt(self):
        """Return the base instruction string for this agent."""
        return (
            f"You are {self.name}, an AI agent. "
            f"Your role: {self.role_description}. "
            "Be concise and focused."
        )

    def _format_context(self, context):
        """Convert context values into labeled text blocks for prompts."""
        if not context:
            return ""

        if isinstance(context, dict):
            blocks = []
            for key, value in context.items():
                if value in (None, "", [], {}):
                    continue
                blocks.append(f"[{str(key).upper()}]\n{value}")
            return "\n\n".join(blocks)

        if isinstance(context, list):
            blocks = []
            for index, value in enumerate(context, start=1):
                if value in (None, "", [], {}):
                    continue
                blocks.append(f"[CONTEXT {index}]\n{value}")
            return "\n\n".join(blocks)

        return str(context)

    def think(self, task, context="", use_rag=True):
        """Generate a response for a task using optional context and RAG examples."""
        prompt = task
        system_prompt = self.system_prompt
        rag_context = ""

        if use_rag:
            examples = get_positive_examples(n=3)
            if examples:
                example_text = "\n\n".join(examples)
                rag_context = (
                    "Here are examples of responses that worked well before:\n"
                    f"{example_text}\n\n"
                    "Now handle this new task:"
                )

        combined_context = self._format_context(context)
        if rag_context:
            combined_context = (
                f"{rag_context}\n\n{combined_context}" if combined_context else rag_context
            )

        if combined_context:
            system_prompt = f"{system_prompt}\n\nContext:\n{combined_context}"

        return call_model(prompt, system_prompt=system_prompt)

    def think_structured(self, task, context="", schema="", use_rag=False):
        """Generate structured JSON output and parse it into a dictionary."""
        structured_task = (
            f"{task}\n\n"
            "Return valid JSON only. Do not include markdown fences or extra prose.\n"
            f"Schema:\n{schema}"
        )
        response = self.think(structured_task, context=context, use_rag=use_rag)
        return self._extract_json(response)

    def _extract_json(self, text):
        """Extract the first JSON object from model output."""
        if not text:
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
