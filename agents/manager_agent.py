# This module defines the manager agent that routes tasks across the ATLAS swarm.
from agents.base_agent import BaseAgent


class ManagerAgent(BaseAgent):
    def __init__(self):
        """Initialize the manager agent with its routing-focused role."""
        super().__init__(
            "Manager",
            "You classify user requests, decide which specialist agents are needed, determine whether live web research is required, and output compact structured routing instructions.",
        )

    def route(self, task, context=""):
        """Return a normalized routing decision for a user request."""
        baseline = self._heuristic_route(task)
        schema = (
            '{'
            '"task_category": "chat|planning|research|execution|hybrid", '
            '"requires_web": false, '
            '"requires_plan": false, '
            '"requires_research": false, '
            '"requires_execution": true, '
            '"parallelizable": false, '
            '"degraded_ok": true, '
            '"reason": "short reason"'
            '}'
        )
        decision = self.think_structured(
            f"Refine this ATLAS route without weakening required capabilities for task: {task}",
            context={
                "baseline_route": baseline,
                "memory": context,
            },
            schema=schema,
            use_rag=False,
        )
        return self._merge_with_baseline(baseline, decision)

    def review_outputs(self, task, context=""):
        """Return an optional refinement decision after the first swarm pass."""
        final_answer = ""
        if isinstance(context, dict):
            final_answer = str(context.get("final_answer", "")).strip()

        if final_answer and len(final_answer) >= 40:
            return {
                "needs_refinement": False,
                "target_agent": "none",
                "followup_instruction": "",
            }

        return {
            "needs_refinement": not bool(final_answer),
            "target_agent": "executor" if not final_answer else "none",
            "followup_instruction": "Make the final answer clearer and directly address the user request." if not final_answer else "",
        }

    def _heuristic_route(self, task):
        """Return the baseline deterministic route for a task."""
        text = task.lower()
        web_keywords = ["latest", "today", "current", "recent", "news", "price", "weather"]
        planning_keywords = ["plan", "steps", "build", "create", "roadmap", "how do i", "how to"]
        research_keywords = ["explain", "compare", "research", "analyze", "summarize", "find", "who is", "what happened"]

        requires_web = any(keyword in text for keyword in web_keywords)
        requires_plan = any(keyword in text for keyword in planning_keywords)
        requires_research = requires_web or any(keyword in text for keyword in research_keywords)
        short_chat = len(task.split()) <= 6 and not requires_web and not requires_plan and not requires_research

        if short_chat:
            task_category = "chat"
        elif requires_plan and requires_research:
            task_category = "hybrid"
        elif requires_plan:
            task_category = "planning"
        elif requires_research:
            task_category = "research"
        else:
            task_category = "execution"

        return {
            "task_category": task_category,
            "requires_web": requires_web,
            "requires_plan": requires_plan,
            "requires_research": requires_research,
            "requires_execution": True,
            "parallelizable": bool(requires_web and requires_plan),
            "degraded_ok": True,
            "reason": "Heuristic baseline route based on request content.",
        }

    def _merge_with_baseline(self, baseline, decision):
        """Merge model refinements without allowing the model to weaken required branches."""
        merged = baseline.copy()

        for key in {"requires_web", "requires_plan", "requires_research", "requires_execution", "parallelizable", "degraded_ok"}:
            merged[key] = baseline.get(key, False)

        reason = str(decision.get("reason", "")).strip()
        if reason and reason.lower() not in {"short reason", "reason"}:
            merged["reason"] = reason

        if merged["requires_web"]:
            merged["requires_research"] = True
            merged["degraded_ok"] = True
        if not merged["requires_execution"]:
            merged["requires_execution"] = True

        return merged
