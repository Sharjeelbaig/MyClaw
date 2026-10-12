"""Planning tools for the planner subagent - read/write operations on .myclaw."""
from langchain.tools import tool
from typing import Optional
import uuid
from datetime import datetime

# Global store instance (initialized by planner subagent)
_myclaw_store = None


def get_store(workspace_root: str) -> "MyClawStore":
    """Get or create the MyClawStore instance."""
    global _myclaw_store
    if _myclaw_store is None:
        from ..context.myclaw_store import MyClawStore
        _myclaw_store = MyClawStore(workspace_root)
    return _myclaw_store


@tool
def read_plan(workspace_root: str, plan_id: Optional[str] = None) -> str:
    """Read a plan from .myclaw/plans/.
    
    Args:
        workspace_root: Root directory of the workspace
        plan_id: Specific plan ID to read, or None for current plan
    
    Returns:
        Plan as markdown string, or error message
    """
    try:
        store = get_store(workspace_root)
        if plan_id:
            plan = store.load_plan(plan_id)
        else:
            plan = store.load_current_plan()
        
        if not plan:
            return "No plan found."
        
        from ..context.myclaw_store import MyClawStore
        return MyClawStore._plan_to_markdown(plan)
    except Exception as e:
        return f"Error reading plan: {e}"


@tool
def write_plan(
    workspace_root: str,
    title: str,
    description: str,
    tasks: list[dict],
    plan_id: Optional[str] = None
) -> str:
    """Write a new plan or update existing plan to .myclaw/plans/.
    
    Args:
        workspace_root: Root directory of the workspace
        title: Plan title
        description: Plan description
        tasks: List of task dicts with 'parent_task' and 'subtasks' keys.
               Each task can have optional 'id' (auto-generated if missing).
               Each subtask can have 'title', 'description', 'done', 'priority'.
        plan_id: Optional existing plan ID to update (creates new version)
    
    Returns:
        Success message with plan ID
    """
    try:
        store = get_store(workspace_root)
        from ..context.context_schema import Plan, TaskBreakdown
        
        def create_task_breakdown(t: dict) -> TaskBreakdown:
            task_data = t.copy()
            if "id" not in task_data:
                task_data["id"] = str(uuid.uuid4())[:8]
            # Ensure subtasks have proper structure
            if "subtasks" in task_data:
                for st in task_data["subtasks"]:
                    if "done" not in st:
                        st["done"] = False
            return TaskBreakdown(**task_data)
        
        if plan_id:
            existing = store.load_plan(plan_id)
            if not existing:
                return f"Plan {plan_id} not found."
            plan = existing.model_copy(update={
                "title": title,
                "description": description,
                "tasks": [create_task_breakdown(t) for t in tasks],
                "updated_at": datetime.now().isoformat(),
                "version": existing.version + 1,
            })
        else:
            plan_id = str(uuid.uuid4())[:8]
            plan = Plan(
                id=plan_id,
                title=title,
                description=description,
                tasks=[create_task_breakdown(t) for t in tasks],
            )
        
        store.save_plan(plan)
        return f"Plan saved: {plan_id} (v{plan.version})"
    except Exception as e:
        return f"Error writing plan: {e}"


@tool
def list_plans(workspace_root: str) -> str:
    """List all plans in .myclaw/plans/plan_history.json."""
    try:
        store = get_store(workspace_root)
        history = store.load_plan_history()
        if not history:
            return "No plans found."
        
        lines = ["## Plan History"]
        for h in history:
            lines.append(f"- **{h['id']}**: {h['title']} ({h['status']}, v{h['version']}) - {h['created_at']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing plans: {e}"


@tool
def read_context(workspace_root: str, project_id: str) -> str:
    """Read full planning context from .myclaw/context/."""
    try:
        store = get_store(workspace_root)
        context = store.load_context(project_id)
        
        lines = [
            f"# Planning Context: {project_id}",
            f"**Updated:** {context.updated_at}",
            "",
        ]
        
        if context.current_plan:
            lines.append("## Current Plan")
            lines.append(f"- **{context.current_plan.title}** ({context.current_plan.status})")
            lines.append(f"  {context.current_plan.description[:200]}...")
        
        if context.file_structure:
            lines.append("\n## File Structure")
            lines.append(f"- Directories: {len(context.file_structure.directories)}")
            lines.append(f"- Files: {len(context.file_structure.files)}")
        
        if context.decisions:
            lines.append(f"\n## Decisions ({len(context.decisions)})")
            for d in context.decisions[-5:]:
                lines.append(f"- {d.title}: {d.rationale[:100]}...")
        
        if context.patterns:
            lines.append(f"\n## Patterns ({len(context.patterns)})")
            for p in context.patterns[-5:]:
                lines.append(f"- {p.name}: {p.description[:100]}...")
        
        if context.research_notes:
            lines.append("\n## Research Notes")
            lines.append(context.research_notes[:500] + "..." if len(context.research_notes) > 500 else context.research_notes)
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading context: {e}"


@tool
def write_context(workspace_root: str, project_id: str, updates: dict) -> str:
    """Update planning context in .myclaw/context/.
    
    Args:
        workspace_root: Root directory
        project_id: Project identifier
        updates: Dict with keys like 'research_notes', 'preferences', etc.
    
    Returns:
        Success message
    """
    try:
        store = get_store(workspace_root)
        context = store.load_context(project_id)
        
        if "research_notes" in updates:
            context.research_notes = updates["research_notes"]
            store.save_research_notes(updates["research_notes"])
        
        if "preferences" in updates:
            context.preferences.update(updates["preferences"])
            store.save_preferences(context.preferences)
        
        store.save_context(context)
        return "Context updated successfully."
    except Exception as e:
        return f"Error updating context: {e}"


@tool
def add_decision(workspace_root: str, title: str, rationale: str, tags: Optional[list[str]] = None) -> str:
    """Record a decision in .myclaw/memory/decisions.json."""
    try:
        store = get_store(workspace_root)
        from ..context.context_schema import Decision
        decision = Decision(
            id=str(uuid.uuid4())[:8],
            title=title,
            rationale=rationale,
            tags=tags or [],
        )
        store.add_decision(decision)
        return f"Decision recorded: {decision.id}"
    except Exception as e:
        return f"Error adding decision: {e}"


@tool
def add_pattern(workspace_root: str, name: str, description: str, example: Optional[str] = None, tags: Optional[list[str]] = None) -> str:
    """Record a learned pattern in .myclaw/memory/patterns.json."""
    try:
        store = get_store(workspace_root)
        from ..context.context_schema import Pattern
        pattern = Pattern(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            example=example,
            tags=tags or [],
        )
        store.add_pattern(pattern)
        return f"Pattern recorded: {pattern.id}"
    except Exception as e:
        return f"Error adding pattern: {e}"


@tool
def scan_workspace(workspace_root: str) -> str:
    """Scan workspace and update file structure memory in .myclaw."""
    try:
        store = get_store(workspace_root)
        from ..context.file_structure import update_file_structure_memory, get_file_structure_summary
        update_file_structure_memory(store)
        return get_file_structure_summary(store)
    except Exception as e:
        return f"Error scanning workspace: {e}"


@tool
def get_file_structure(workspace_root: str) -> str:
    """Get current file structure summary from .myclaw."""
    try:
        store = get_store(workspace_root)
        from ..context.file_structure import get_file_structure_summary
        return get_file_structure_summary(store)
    except Exception as e:
        return f"Error getting file structure: {e}"


@tool
def find_files(workspace_root: str, pattern: str) -> str:
    """Find files matching a pattern in workspace."""
    try:
        store = get_store(workspace_root)
        from ..context.file_structure import find_files_by_pattern
        matches = find_files_by_pattern(store, pattern)
        if not matches:
            return f"No files matching '{pattern}'"
        return "Matching files:\n" + "\n".join(f"  📄 {f}" for f in matches)
    except Exception as e:
        return f"Error finding files: {e}"


@tool
def search_decisions(workspace_root: str, query: str, tags: Optional[list[str]] = None) -> str:
    """Search past decisions in .myclaw/memory/decisions.json.
    
    Args:
        workspace_root: Root directory
        query: Search term
        tags: Optional tags to filter by
    
    Returns:
        Matching decisions
    """
    try:
        store = get_store(workspace_root)
        decisions = store.get_decisions(tags)
        
        query_lower = query.lower()
        matches = [d for d in decisions if query_lower in d.title.lower() or query_lower in d.rationale.lower()]
        
        if not matches:
            return f"No decisions matching '{query}'"
        
        lines = [f"# Decisions matching '{query}' ({len(matches)} found)", ""]
        for d in matches:
            lines.append(f"## {d.title} ({d.id})")
            lines.append(f"**Tags:** {', '.join(d.tags) if d.tags else 'none'}")
            lines.append(f"**Rationale:** {d.rationale}")
            lines.append(f"**Date:** {d.timestamp}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching decisions: {e}"


@tool
def search_patterns(workspace_root: str, query: str, tags: Optional[list[str]] = None) -> str:
    """Search learned patterns in .myclaw/memory/patterns.json.
    
    Args:
        workspace_root: Root directory
        query: Search term
        tags: Optional tags to filter by
    
    Returns:
        Matching patterns
    """
    try:
        store = get_store(workspace_root)
        patterns = store.get_patterns(tags)
        
        query_lower = query.lower()
        matches = [p for p in patterns if query_lower in p.name.lower() or query_lower in p.description.lower()]
        
        if not matches:
            return f"No patterns matching '{query}'"
        
        lines = [f"# Patterns matching '{query}' ({len(matches)} found)", ""]
        for p in matches:
            lines.append(f"## {p.name} ({p.id})")
            lines.append(f"**Tags:** {', '.join(p.tags) if p.tags else 'none'}")
            lines.append(f"**Description:** {p.description}")
            if p.example:
                lines.append(f"**Example:** {p.example}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching patterns: {e}"


@tool
def get_project_overview(workspace_root: str, project_id: str) -> str:
    """Get comprehensive project overview from .myclaw context.
    
    Args:
        workspace_root: Root directory
        project_id: Project identifier
    
    Returns:
        Full project overview
    """
    try:
        store = get_store(workspace_root)
        from ..context.myclaw_store import MyClawStore
        from ..context.file_structure import get_file_structure_summary
        
        context = store.load_context(project_id)
        
        lines = [f"# Project Overview: {project_id}", ""]
        
        if context.current_plan:
            p = context.current_plan
            lines.extend([
                "## Current Plan",
                f"- **{p.title}** ({p.status}, v{p.version})",
                f"- {p.description}",
                f"- {len(p.tasks)} task groups",
                "",
            ])
        
        lines.append("## File Structure")
        lines.append(get_file_structure_summary(store))
        lines.append("")
        
        if context.decisions:
            lines.append("## Recent Decisions")
            for d in context.decisions[-3:]:
                lines.append(f"- **{d.title}**: {d.rationale[:150]}...")
            lines.append("")
        
        if context.patterns:
            lines.append("## Active Patterns")
            for p in context.patterns[-3:]:
                lines.append(f"- **{p.name}**: {p.description[:150]}...")
            lines.append("")
        
        if context.preferences:
            lines.append("## Preferences")
            for k, v in context.preferences.items():
                lines.append(f"- {k}: {v}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting project overview: {e}"