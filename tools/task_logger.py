# This module logs ATLAS tasks to SQLite and displays recent history in a table.
from datetime import datetime
import json

from rich.console import Console
from rich.table import Table
from sqlite_utils import Database

import config


console = Console()


def _get_database():
    """Create or return the ATLAS SQLite database and tasks table."""
    db = Database(config.SQLITE_DB_PATH)
    table = db["tasks"]
    table.create(
        {
            "id": int,
            "timestamp": str,
            "user_input": str,
            "agent_used": str,
            "result": str,
            "status": str,
            "metadata": str,
        },
        pk="id",
        if_not_exists=True,
    )
    if "metadata" not in table.columns_dict:
        table.add_column("metadata", str)
    return db


def log_task(user_input, agent_used, result, status="success", metadata=None):
    """Insert a task record into the SQLite task log."""
    db = _get_database()
    db["tasks"].insert(
        {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_used": agent_used,
            "result": result,
            "status": status,
            "metadata": json.dumps(metadata or {}),
        }
    )


def get_recent_tasks(n=10):
    """Return the most recent task records as a list of dictionaries."""
    db = _get_database()
    query = """
        select id, timestamp, user_input, agent_used, result, status, metadata
        from tasks
        order by id desc
        limit ?
    """
    rows = list(db.query(query, [n]))
    for row in rows:
        try:
            row["metadata"] = json.loads(row.get("metadata") or "{}")
        except json.JSONDecodeError:
            row["metadata"] = {}
    return rows


def print_task_history():
    """Print the recent ATLAS task history in a formatted rich table."""
    tasks = get_recent_tasks()
    table = Table(title="Recent ATLAS Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("User Input", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Meta", style="magenta")
    table.add_column("Result", style="green")

    for task in tasks:
        meta = task.get("metadata") or {}
        meta_summary = " ".join(
            f"[{key}:{value}]"
            for key, value in meta.items()
            if key in {"used_web", "web_status", "degraded_mode", "task_category"}
        )
        result_preview = str(task["result"]).replace("\n", " ").strip()
        if len(result_preview) > 80:
            result_preview = f"{result_preview[:77]}..."
        table.add_row(
            str(task["id"]),
            task["user_input"],
            task["status"],
            meta_summary,
            result_preview,
        )

    console.print(table)
