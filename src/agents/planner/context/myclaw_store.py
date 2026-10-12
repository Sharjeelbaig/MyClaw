"""File-based storage for .myclaw folder - handles all persistence."""
import json
import os
from pathlib import Path
from typing import Any

from .context_schema import (
    PlanningContext,
    Plan,
    Decision,
    Pattern,
    FileStructure,
    TaskBreakdown,
    create_empty_context,
)


class MyClawStore:
    """Manages the .myclaw folder in the workspace for planning artifacts."""

    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()
        self.myclaw_dir = self.workspace_root / ".myclaw"
        self._ensure_structure()

    def _ensure_structure(self):
        """Create .myclaw directory structure if it doesn't exist."""
        dirs = [
            self.myclaw_dir / "plans",
            self.myclaw_dir / "context",
            self.myclaw_dir / "memory",
            self.myclaw_dir / "skills",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # --- Plan operations ---
    def save_plan(self, plan: Plan) -> None:
        """Save a plan to .myclaw/plans/"""
        plan_file = self.myclaw_dir / "plans" / f"{plan.id}.json"
        plan_data = plan.model_dump()
        plan_data["updated_at"] = plan.updated_at
        plan_file.write_text(json.dumps(plan_data, indent=2))

        # Also update current_plan.md for quick reading
        current_file = self.myclaw_dir / "plans" / "current_plan.md"
        current_file.write_text(self._plan_to_markdown(plan))

        # Update plan history
        self._append_to_history(plan)

    def _append_to_history(self, plan: Plan) -> None:
        history_file = self.myclaw_dir / "plans" / "plan_history.json"
        history = []
        if history_file.exists():
            history = json.loads(history_file.read_text())
        history.append({
            "id": plan.id,
            "title": plan.title,
            "status": plan.status,
            "created_at": plan.created_at,
            "version": plan.version,
        })
        history_file.write_text(json.dumps(history, indent=2))

    def load_plan(self, plan_id: str) -> Plan | None:
        """Load a specific plan by ID."""
        plan_file = self.myclaw_dir / "plans" / f"{plan_id}.json"
        if not plan_file.exists():
            return None
        data = json.loads(plan_file.read_text())
        return Plan(**data)

    def load_current_plan(self) -> Plan | None:
        """Load the most recent plan."""
        history_file = self.myclaw_dir / "plans" / "plan_history.json"
        if not history_file.exists():
            return None
        history = json.loads(history_file.read_text())
        if not history:
            return None
        latest = history[-1]
        return self.load_plan(latest["id"])

    def load_plan_history(self) -> list[dict]:
        """Load plan history summary."""
        history_file = self.myclaw_dir / "plans" / "plan_history.json"
        if not history_file.exists():
            return []
        return json.loads(history_file.read_text())

    def _plan_to_markdown(self, plan: Plan) -> str:
        """Convert plan to markdown for human reading."""
        lines = [
            f"# {plan.title}",
            f"**ID:** {plan.id}  |  **Status:** {plan.status}  |  **Version:** {plan.version}",
            f"**Created:** {plan.created_at}  |  **Updated:** {plan.updated_at}",
            "",
            f"## Description",
            plan.description,
            "",
            "## Tasks",
        ]
        for task in plan.tasks:
            lines.append(f"\n### {task.parent_task} ({task.status})")
            lines.append(f"**ID:** {task.id}")
            for st in task.subtasks:
                status_icon = "✓" if st.get("done") else "○"
                lines.append(f"  {status_icon} {st.get('title', 'Untitled')}")
        return "\n".join(lines)

    # --- Context operations ---
    def save_context(self, context: PlanningContext) -> None:
        """Save full context to .myclaw/context/"""
        context_file = self.myclaw_dir / "context" / "planning_context.json"
        context.updated_at = __import__("datetime").datetime.now().isoformat()
        context_file.write_text(context.model_dump_json(indent=2))

    def load_context(self, project_id: str) -> PlanningContext:
        """Load context or create empty if not exists."""
        context_file = self.myclaw_dir / "context" / "planning_context.json"
        if not context_file.exists():
            return create_empty_context(project_id)
        data = json.loads(context_file.read_text())
        data["project_id"] = project_id
        return PlanningContext(**data)

    # --- File structure operations ---
    def save_file_structure(self, fs: FileStructure) -> None:
        """Save file structure snapshot."""
        fs_file = self.myclaw_dir / "context" / "file_structure.json"
        fs.updated_at = __import__("datetime").datetime.now().isoformat()
        fs_file.write_text(fs.model_dump_json(indent=2))

    def load_file_structure(self) -> FileStructure | None:
        """Load file structure snapshot."""
        fs_file = self.myclaw_dir / "context" / "file_structure.json"
        if not fs_file.exists():
            return None
        data = json.loads(fs_file.read_text())
        return FileStructure(**data)

    # --- Decision operations ---
    def add_decision(self, decision: Decision) -> None:
        """Add a decision to memory."""
        decisions_file = self.myclaw_dir / "memory" / "decisions.json"
        decisions = []
        if decisions_file.exists():
            decisions = json.loads(decisions_file.read_text())
        decisions.append(decision.model_dump())
        decisions_file.write_text(json.dumps(decisions, indent=2))

    def get_decisions(self, tags: list[str] | None = None) -> list[Decision]:
        """Get decisions, optionally filtered by tags."""
        decisions_file = self.myclaw_dir / "memory" / "decisions.json"
        if not decisions_file.exists():
            return []
        decisions = [Decision(**d) for d in json.loads(decisions_file.read_text())]
        if tags:
            decisions = [d for d in decisions if any(t in d.tags for t in tags)]
        return decisions

    # --- Pattern operations ---
    def add_pattern(self, pattern: Pattern) -> None:
        """Add a learned pattern."""
        patterns_file = self.myclaw_dir / "memory" / "patterns.json"
        patterns = []
        if patterns_file.exists():
            patterns = json.loads(patterns_file.read_text())
        patterns.append(pattern.model_dump())
        patterns_file.write_text(json.dumps(patterns, indent=2))

    def get_patterns(self, tags: list[str] | None = None) -> list[Pattern]:
        """Get patterns, optionally filtered by tags."""
        patterns_file = self.myclaw_dir / "memory" / "patterns.json"
        if not patterns_file.exists():
            return []
        patterns = [Pattern(**p) for p in json.loads(patterns_file.read_text())]
        if tags:
            patterns = [p for p in patterns if any(t in p.tags for t in tags)]
        return patterns

    # --- Research notes ---
    def save_research_notes(self, notes: str) -> None:
        """Save research notes."""
        notes_file = self.myclaw_dir / "context" / "research_notes.md"
        notes_file.write_text(notes)

    def load_research_notes(self) -> str:
        """Load research notes."""
        notes_file = self.myclaw_dir / "context" / "research_notes.md"
        if not notes_file.exists():
            return ""
        return notes_file.read_text()

    # --- Preferences ---
    def save_preferences(self, prefs: dict[str, Any]) -> None:
        """Save user preferences."""
        prefs_file = self.myclaw_dir / "memory" / "preferences.json"
        prefs_file.write_text(json.dumps(prefs, indent=2))

    def load_preferences(self) -> dict[str, Any]:
        """Load user preferences."""
        prefs_file = self.myclaw_dir / "memory" / "preferences.json"
        if not prefs_file.exists():
            return {}
        return json.loads(prefs_file.read_text())

    # --- Utility ---
    def scan_workspace_structure(self) -> FileStructure:
        """Scan workspace and return file structure."""
        dirs = []
        files = []
        for root, dnames, fnames in os.walk(self.workspace_root):
            # Skip .myclaw and hidden dirs
            rel_root = Path(root).relative_to(self.workspace_root)
            if ".myclaw" in rel_root.parts or any(p.startswith(".") for p in rel_root.parts):
                continue
            for d in dnames:
                if not d.startswith("."):
                    dirs.append(str(rel_root / d))
            for f in fnames:
                if not f.startswith("."):
                    files.append(str(rel_root / f))
        return FileStructure(
            root=str(self.workspace_root),
            directories=sorted(dirs),
            files=sorted(files),
        )