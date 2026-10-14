import json
from pathlib import Path

from langchain.tools import ToolRuntime

from config import WORKSPACE_ROOT
from agents.planner.classes.Todo import Todo


def todos_file(runtime: ToolRuntime) -> Path:
    thread_id = runtime.execution_info.thread_id
    return WORKSPACE_ROOT / ".myclaw" / "sessions" / thread_id / "todos.json"


def load_todos(runtime: ToolRuntime) -> dict[str, Todo]:
    path = todos_file(runtime)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {tid: Todo.model_validate(data) for tid, data in raw.items()}


def save_todos(runtime: ToolRuntime, todos: dict[str, Todo]) -> None:
    path = todos_file(runtime)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = {tid: todo.model_dump() for tid, todo in todos.items()}
    path.write_text(json.dumps(raw, indent=2))
