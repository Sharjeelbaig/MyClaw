"""Context retrieval skills for the planner subagent."""
from langchain.tools import tool
from typing import Optional


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
        from ..context.myclaw_store import MyClawStore
        store = MyClawStore(workspace_root)
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
        from ..context.myclaw_store import MyClawStore
        store = MyClawStore(workspace_root)
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
        from ..context.myclaw_store import MyClawStore
        from ..context.file_structure import get_file_structure_summary
        
        store = MyClawStore(workspace_root)
        context = store.load_context(project_id)
        
        lines = [f"# Project Overview: {project_id}", ""]
        
        # Current plan
        if context.current_plan:
            p = context.current_plan
            lines.extend([
                "## Current Plan",
                f"- **{p.title}** ({p.status}, v{p.version})",
                f"- {p.description}",
                f"- {len(p.tasks)} task groups",
                "",
            ])
        
        # File structure
        lines.append("## File Structure")
        lines.append(get_file_structure_summary(store))
        lines.append("")
        
        # Recent decisions
        if context.decisions:
            lines.append("## Recent Decisions")
            for d in context.decisions[-3:]:
                lines.append(f"- **{d.title}**: {d.rationale[:150]}...")
            lines.append("")
        
        # Active patterns
        if context.patterns:
            lines.append("## Active Patterns")
            for p in context.patterns[-3:]:
                lines.append(f"- **{p.name}**: {p.description[:150]}...")
            lines.append("")
        
        # Preferences
        if context.preferences:
            lines.append("## Preferences")
            for k, v in context.preferences.items():
                lines.append(f"- {k}: {v}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting project overview: {e}"