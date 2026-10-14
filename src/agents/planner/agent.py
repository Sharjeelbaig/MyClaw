from agents.planner.prompt import SYSTEM_PROMPT
from agents.planner.tools.create_or_update_todo import createOrUpdateTodo
from agents.planner.tools.render_todo_board import renderTodoBoard


def create_planner_subagent(model) -> dict:
    return {
        "name": "planner-agent",
        "description": "Used for planning the steps to complete user requests. It can create and manage todo boards and tasks.",
        "system_prompt": SYSTEM_PROMPT,
        "tools": [createOrUpdateTodo, renderTodoBoard],
        "model": model,
    }
