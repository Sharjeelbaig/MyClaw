"""Planning skills for the planner subagent."""
from langchain.tools import tool
from typing import Optional
import uuid
from datetime import datetime


@tool
def create_task_breakdown(parent_task: str, subtasks: list[dict]) -> str:
    """Create a structured task breakdown for planning.
    
    Args:
        parent_task: The main task description
        subtasks: List of dicts with 'title', 'description', 'priority' (high/medium/low), 'estimated_hours'
    
    Returns:
        Formatted task breakdown
    """
    lines = [f"# Task Breakdown: {parent_task}", ""]
    for i, st in enumerate(subtasks, 1):
        priority = st.get("priority", "medium")
        hours = st.get("estimated_hours", "?")
        lines.append(f"## {i}. {st.get('title', 'Untitled')}")
        lines.append(f"   **Priority:** {priority}  |  **Est. Hours:** {hours}")
        lines.append(f"   {st.get('description', 'No description')}")
        lines.append("")
    return "\n".join(lines)


@tool
def prioritize_tasks(tasks: list[dict], criteria: str = "impact") -> str:
    """Prioritize a list of tasks based on criteria.
    
    Args:
        tasks: List of task dicts with 'title', 'impact', 'effort', 'urgency'
        criteria: 'impact', 'effort', 'urgency', or 'ice' (Impact*Confidence/Effort)
    
    Returns:
        Prioritized task list
    """
    def score(t):
        impact = t.get("impact", 5)
        effort = t.get("effort", 5)
        urgency = t.get("urgency", 5)
        confidence = t.get("confidence", 5)
        
        if criteria == "impact":
            return -impact
        elif criteria == "effort":
            return effort
        elif criteria == "urgency":
            return -urgency
        elif criteria == "ice":
            return -((impact * confidence) / max(effort, 1))
        return 0
    
    sorted_tasks = sorted(tasks, key=score)
    lines = [f"# Prioritized Tasks (by {criteria.upper()})", ""]
    for i, t in enumerate(sorted_tasks, 1):
        lines.append(f"{i}. **{t.get('title')}** - Impact: {t.get('impact',5)}/10, Effort: {t.get('effort',5)}/10, Urgency: {t.get('urgency',5)}/10")
    return "\n".join(lines)


@tool
def estimate_effort(task_description: str, complexity: str = "medium") -> str:
    """Estimate effort for a task.
    
    Args:
        task_description: Description of the task
        complexity: 'low', 'medium', 'high', 'very_high'
    
    Returns:
        Effort estimate with breakdown
    """
    base_hours = {"low": 1, "medium": 4, "high": 16, "very_high": 40}
    hours = base_hours.get(complexity, 4)
    
    lines = [
        f"# Effort Estimate",
        f"**Task:** {task_description}",
        f"**Complexity:** {complexity}",
        f"**Estimated Hours:** {hours}",
        "",
        "## Breakdown:",
    ]
    
    if complexity == "low":
        lines.extend(["- Research/design: 0.5h", "- Implementation: 0.5h"])
    elif complexity == "medium":
        lines.extend(["- Research/design: 1h", "- Implementation: 2h", "- Testing: 1h"])
    elif complexity == "high":
        lines.extend(["- Research/design: 4h", "- Implementation: 8h", "- Testing: 4h"])
    else:
        lines.extend(["- Research/design: 8h", "- Implementation: 24h", "- Testing: 8h"])
    
    return "\n".join(lines)


@tool
def identify_dependencies(tasks: list[dict]) -> str:
    """Identify dependencies between tasks.
    
    Args:
        tasks: List of task dicts with 'id', 'title', 'depends_on' (list of task IDs)
    
    Returns:
        Dependency graph and execution order
    """
    # Build adjacency list
    task_map = {t["id"]: t for t in tasks}
    visited = set()
    order = []
    
    def visit(task_id):
        if task_id in visited:
            return
        visited.add(task_id)
        for dep in task_map.get(task_id, {}).get("depends_on", []):
            visit(dep)
        order.append(task_id)
    
    for t in tasks:
        visit(t["id"])
    
    lines = ["# Task Dependencies", "", "## Execution Order:"]
    for i, tid in enumerate(order, 1):
        t = task_map[tid]
        deps = t.get("depends_on", [])
        dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
        lines.append(f"{i}. {t['title']}{dep_str}")
    
    # Find parallelizable groups
    lines.append("\n## Parallel Groups (can run simultaneously):")
    # Simple grouping by dependency depth
    depth = {}
    def get_depth(tid):
        if tid in depth:
            return depth[tid]
        deps = task_map.get(tid, {}).get("depends_on", [])
        d = 0 if not deps else max(get_depth(d) for d in deps) + 1
        depth[tid] = d
        return d
    
    for t in tasks:
        get_depth(t["id"])
    
    max_depth = max(depth.values()) if depth else 0
    for d in range(max_depth + 1):
        group = [task_map[tid]["title"] for tid in depth if depth[tid] == d]
        if group:
            lines.append(f"  Level {d}: {', '.join(group)}")
    
    return "\n".join(lines)