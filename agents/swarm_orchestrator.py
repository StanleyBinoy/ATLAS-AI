# This module coordinates manager-routed swarm execution for ATLAS.
from concurrent.futures import ThreadPoolExecutor
import json

from agents.executor_agent import ExecutorAgent
from agents.manager_agent import ManagerAgent
from agents.planner_agent import PlannerAgent
from agents.researcher_agent import ResearcherAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.web_research_agent import WebResearchAgent
from memory.chroma_store import save_memory, search_memory
from tools.task_logger import log_task
from tools.web_search import browse_and_summarize


class SwarmOrchestrator:
    def __init__(self):
        """Initialize the manager-routed ATLAS swarm and its specialist agents."""
        self.manager = ManagerAgent()
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.executor = ExecutorAgent()
        self.web_researcher = WebResearchAgent()
        self.synthesizer = SynthesizerAgent()

    def run_swarm_task(self, user_input, status_callback=None, output_callback=None):
        """Run a full swarm workflow and return orchestration details."""
        status_callback = status_callback or (lambda message: None)
        output_callback = output_callback or (lambda name, message: None)

        memories = search_memory(user_input)
        memory_context = "\n".join(memories) if memories else ""

        status_callback("Manager is routing your request...")
        routing = self.manager.route(user_input, context={"memory": memory_context})
        manager_summary = self._format_manager_summary(routing)
        output_callback("Manager", manager_summary)

        agent_outputs = {
            "manager": manager_summary,
            "planner": "",
            "researcher": "",
            "web_researcher": "",
            "executor": "",
        }
        web_result = {
            "query": user_input,
            "search_results": [],
            "pages": [],
            "success": False,
            "web_status": "unavailable",
            "error_message": "",
            "sources": [],
        }
        final_answer = ""

        if routing["requires_plan"] and routing["requires_web"] and routing["parallelizable"]:
            status_callback("Parallel swarm branches are running...")
            with ThreadPoolExecutor(max_workers=2) as executor_pool:
                planner_future = executor_pool.submit(
                    self._safe_agent_call,
                    self.planner,
                    user_input,
                    {
                        "memory": memory_context,
                        "instruction": "Return numbered planning steps only.",
                    },
                    False,
                )
                web_future = executor_pool.submit(self._run_live_web_research, user_input)
                agent_outputs["planner"] = planner_future.result()
                web_result = web_future.result()
        else:
            if routing["requires_plan"]:
                agent_outputs["planner"] = self._safe_agent_call(
                    self.planner,
                    user_input,
                    {
                        "memory": memory_context,
                        "instruction": "Return numbered planning steps only.",
                    },
                    False,
                )
            if routing["requires_web"]:
                web_result = self._run_live_web_research(user_input)

        if agent_outputs["planner"]:
            output_callback("Planner", agent_outputs["planner"])

        if routing["requires_web"]:
            if web_result["web_status"] == "success":
                agent_outputs["web_researcher"] = self._safe_agent_call(
                    self.web_researcher,
                    user_input,
                    {
                        "memory": memory_context,
                        "search_results": self._stringify_web_results(web_result["search_results"]),
                        "page_summaries": self._stringify_pages(web_result["pages"]),
                        "sources": self._stringify_sources(web_result["sources"]),
                        "instruction": "Summarize only the supplied web findings and include source URLs.",
                    },
                    False,
                )
                output_callback("WebResearcher", agent_outputs["web_researcher"])
            else:
                output_callback("WebResearcher", f"Live web search unavailable. {web_result['error_message']}")

        if routing["requires_research"] and web_result["web_status"] == "success":
            status_callback("Researcher is organizing the gathered context...")
            agent_outputs["researcher"] = self._safe_agent_call(
                self.researcher,
                user_input,
                {
                    "memory": memory_context,
                    "plan": agent_outputs["planner"],
                    "web_notes": agent_outputs["web_researcher"],
                    "web_status": self._researcher_web_instruction(web_result["web_status"]),
                    "sources": self._stringify_sources(web_result["sources"]),
                    "instruction": "Return concise evidence-based research notes only.",
                },
                False,
            )
            output_callback("Researcher", agent_outputs["researcher"])

        if routing["requires_execution"] and (not routing["requires_web"] or web_result["web_status"] == "success"):
            status_callback("Executor is working on the coordinated plan...")
            agent_outputs["executor"] = self._safe_agent_call(
                self.executor,
                user_input,
                {
                    "memory": memory_context,
                    "plan": agent_outputs["planner"],
                    "research": agent_outputs["researcher"],
                    "web_notes": agent_outputs["web_researcher"],
                    "web_status": self._executor_web_instruction(web_result["web_status"]),
                    "sources": self._stringify_sources(web_result["sources"]),
                    "instruction": "Draft a concrete answer, not action narration.",
                },
                False,
            )
            output_callback("Executor", agent_outputs["executor"])

        if routing["requires_web"] and web_result["web_status"] != "success":
            final_answer = self._build_degraded_web_answer(user_input, web_result)
        else:
            status_callback("Synthesizer is merging the swarm outputs...")
            final_answer = self._safe_agent_call(
                self.synthesizer,
                user_input,
                {
                    "memory": memory_context,
                    "routing": json.dumps(routing, indent=2),
                    "planner": agent_outputs["planner"],
                    "researcher": agent_outputs["researcher"],
                    "web_researcher": agent_outputs["web_researcher"],
                    "executor": agent_outputs["executor"],
                    "sources": self._stringify_sources(web_result["sources"]),
                    "instruction": self._synthesizer_instruction(web_result["web_status"]),
                },
                False,
            )

        if not final_answer.strip():
            final_answer = self._fallback_final_answer(user_input, agent_outputs, web_result)

        degraded_mode = web_result["web_status"] != "success" and routing["requires_web"]
        exchange = (
            f"User: {user_input}\n\n"
            f"Routing:\n{json.dumps(routing, indent=2)}\n\n"
            f"Planner:\n{agent_outputs['planner']}\n\n"
            f"Researcher:\n{agent_outputs['researcher']}\n\n"
            f"WebResearcher:\n{agent_outputs['web_researcher']}\n\n"
            f"Executor:\n{agent_outputs['executor']}\n\n"
            f"ATLAS:\n{final_answer}"
        )

        save_memory(
            (
                f"User: {user_input}\n\n"
                f"Routing summary: {routing['task_category']} | web={routing['requires_web']} | plan={routing['requires_plan']}\n\n"
                f"Key research notes:\n{agent_outputs['researcher'] or agent_outputs['web_researcher']}\n\n"
                f"Final answer:\n{final_answer}"
            ),
            metadata={
                "feedback": "neutral",
                "task_category": routing["task_category"],
                "used_web": str(routing["requires_web"]).lower(),
                "web_status": web_result["web_status"],
                "degraded_mode": str(degraded_mode).lower(),
            },
        )

        metadata = {
            "selected_agents": self._selected_agents_from_route(routing),
            "used_web": routing["requires_web"],
            "web_status": web_result["web_status"],
            "degraded_mode": degraded_mode,
            "task_category": routing["task_category"],
        }
        log_task(user_input, "swarm", final_answer, status="success", metadata=metadata)

        return {
            "routing": routing,
            "selected_agents": self._selected_agents_from_route(routing),
            "agent_outputs": agent_outputs,
            "web_status": web_result["web_status"],
            "sources": web_result["sources"],
            "degraded_mode": degraded_mode,
            "final_answer": final_answer,
            "exchange": exchange,
            "web_result": web_result,
        }

    def _run_live_web_research(self, user_input):
        """Perform live web retrieval and normalize failures into a stable contract."""
        bundle = browse_and_summarize(user_input, max_results=3)
        return {
            "query": user_input,
            "search_results": bundle.get("search_results", []),
            "pages": bundle.get("pages", []),
            "success": bundle.get("success", False),
            "web_status": bundle.get("web_status", "unavailable"),
            "error_message": bundle.get("error_message", ""),
            "sources": bundle.get("sources", []),
        }

    def _safe_agent_call(self, agent, task, context, use_rag=True):
        """Run an agent and isolate failures into visible outputs."""
        try:
            return agent.think(task, context=context, use_rag=use_rag)
        except Exception as exc:
            return f"Agent failure: {exc}"

    def _selected_agents_from_route(self, routing):
        """Return the selected agent names for a routing decision."""
        selected = ["Manager", "Synthesizer"]
        if routing["requires_plan"]:
            selected.append("Planner")
        if routing["requires_research"]:
            selected.append("Researcher")
        if routing["requires_web"]:
            selected.append("WebResearcher")
        if routing["requires_execution"]:
            selected.append("Executor")
        return selected

    def _format_manager_summary(self, routing):
        """Return a readable summary of the manager routing decision."""
        selected = ", ".join(self._selected_agents_from_route(routing))
        return (
            f"Task category: {routing['task_category']}\n"
            f"Selected agents: {selected}\n"
            f"Requires web: {routing['requires_web']}\n"
            f"Requires plan: {routing['requires_plan']}\n"
            f"Parallelizable: {routing['parallelizable']}\n"
            f"Reason: {routing['reason']}"
        )

    def _researcher_web_instruction(self, web_status):
        """Return the web-status instruction for the researcher."""
        if web_status == "success":
            return "Use only the provided web findings and cite the supplied sources."
        return "Live web retrieval was unavailable. Use local reasoning only and do not claim you accessed the internet."

    def _executor_web_instruction(self, web_status):
        """Return the web-status instruction for the executor."""
        if web_status == "success":
            return "Use the provided evidence to draft a concrete answer."
        return "Live web retrieval was unavailable. Draft an answer from local reasoning only and say so briefly if the task asks for current information."

    def _synthesizer_instruction(self, web_status):
        """Return the final synthesis instruction based on web status."""
        if web_status == "success":
            return "Produce the final user-facing answer only. Include a short Sources section using the provided URLs."
        return "Produce the final user-facing answer only. Clearly note that live web retrieval was unavailable and avoid fabricated current claims."

    def _fallback_final_answer(self, user_input, agent_outputs, web_result):
        """Return a simple fallback final answer if synthesis returns nothing."""
        pieces = [agent_outputs["executor"], agent_outputs["researcher"], agent_outputs["planner"]]
        best = next((piece for piece in pieces if piece and "Agent failure:" not in piece), "")
        if best:
            if web_result["web_status"] != "success":
                return f"{best}\n\nNote: Live web retrieval was unavailable."
            return best
        return f"I could not assemble a full answer for: {user_input}"

    def _build_degraded_web_answer(self, user_input, web_result):
        """Return a safe degraded answer for web-dependent requests when retrieval fails."""
        return (
            "Live web retrieval was unavailable for this request, so I cannot reliably provide current web-based information from this environment.\n\n"
            f"Request: {user_input}\n"
            f"Web status: {web_result['web_status']}\n"
            f"Error: {web_result['error_message']}\n\n"
            "Try again when network search is available, or provide a source URL for me to summarize."
        )

    def _stringify_web_results(self, results):
        """Convert web search results into a prompt-friendly string."""
        return "\n".join(
            f"- {result.get('title', 'Untitled')} | {result.get('url', '')} | {result.get('snippet', '')}"
            for result in results
        )

    def _stringify_pages(self, pages):
        """Convert fetched page payloads into a prompt-friendly string."""
        lines = []
        for page in pages:
            if not page.get("success"):
                lines.append(f"- {page.get('url', '')} | fetch failed: {page.get('error', '')}")
            else:
                lines.append(
                    f"- {page.get('title', page.get('url', ''))} | {page.get('url', '')}\n"
                    f"  {page.get('content', '')[:400]}"
                )
        return "\n".join(lines)

    def _stringify_sources(self, sources):
        """Convert source dictionaries into a prompt-friendly string."""
        return "\n".join(
            f"- {source.get('title', '')}: {source.get('url', '')}" for source in sources
        )
