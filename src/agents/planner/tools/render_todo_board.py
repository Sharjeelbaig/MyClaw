from langchain.tools import tool, ToolRuntime

from agents.planner.store import load_todos


@tool
def renderTodoBoard(runtime: ToolRuntime) -> str:
    """Render the current todo board as markdown."""
    todos = load_todos(runtime)
    if not todos:
        return "No todos yet."

    lines = ["# Todo Board", ""]
    for todo in todos.values():
        lines.append(f"## {todo.title}")
        lines.append(f"_{todo.description}_")
        lines.append("")
        for status in ("todo", "in_progress", "done"):
            tasks = [t for t in todo.tasks if t.status == status]
            if not tasks:
                continue
            lines.append(f"**{status}**")
            for t in tasks:
                mark = "x" if status == "done" else " "
                lines.append(f"- [{mark}] ({t.ticket_id}) {t.title}")
            lines.append("")
    return "\n".join(lines)
