"""Pydantic models for planning context data structures."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class Decision(BaseModel):
    """A recorded decision with rationale."""
    id: str
    title: str
    rationale: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = Field(default_factory=list)


class Pattern(BaseModel):
    """A learned pattern or best practice."""
    id: str
    name: str
    description: str
    example: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FileStructure(BaseModel):
    """Project file structure snapshot."""
    root: str
    directories: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskBreakdown(BaseModel):
    """A task broken down into subtasks."""
    id: str
    parent_task: str
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "pending"  # pending, in_progress, done
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Plan(BaseModel):
    """A complete plan with metadata."""
    id: str
    title: str
    description: str
    tasks: list[TaskBreakdown] = Field(default_factory=list)
    status: str = "draft"  # draft, active, completed, archived
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class PlanningContext(BaseModel):
    """Complete planning context for the planner subagent."""
    project_id: str
    current_plan: Plan | None = None
    plan_history: list[Plan] = Field(default_factory=list)
    file_structure: FileStructure | None = None
    decisions: list[Decision] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    research_notes: str = ""
    preferences: dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Default empty context factory
def create_empty_context(project_id: str) -> PlanningContext:
    """Create an empty planning context for a new project."""
    return PlanningContext(project_id=project_id)