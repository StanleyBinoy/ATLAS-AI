# This module provides rich-based console input and output helpers for ATLAS.
import locale

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


console = Console()


def _safe_text(message):
    """Convert text into a form that can be printed by the current terminal encoding."""
    encoding = locale.getpreferredencoding(False) or "utf-8"
    return str(message).encode(encoding, errors="replace").decode(encoding)


def print_banner():
    """Print the ATLAS banner and subtitle in a styled panel."""
    banner = Text(
        "\n"
        "   ___  ________    ___   _____\n"
        "  / _ |/_  __/ /   / _ | / ___/\n"
        " / __ | / / / /__ / __ |/ /__  \n"
        "/_/ |_|/_/ /____//_/ |_|\\___/  \n",
        style="bold cyan",
    )
    subtitle = Text("Adaptive Task-Learning Agent System", style="cyan")
    console.print(Panel.fit(Text.assemble(banner, subtitle), border_style="cyan"))


def print_success(message):
    """Print a success message in green."""
    console.print(Text(f"[OK] {_safe_text(message)}", style="green"))


def print_error(message):
    """Print an error message in red."""
    console.print(Text(f"[ERROR] {_safe_text(message)}", style="red"))


def print_thinking(message):
    """Print a thinking status message in yellow."""
    console.print(Text(f"[...] {_safe_text(message)}", style="yellow"))


def print_agent_response(agent_name, message):
    """Print an agent name followed by its response message."""
    header = Text(_safe_text(agent_name), style="bold blue")
    body = Text(_safe_text(message))
    console.print(header)
    console.print(body)


def prompt_user(question):
    """Prompt the user for input and return the typed response."""
    return console.input(f"[bold cyan]{_safe_text(question)}[/bold cyan] ")
