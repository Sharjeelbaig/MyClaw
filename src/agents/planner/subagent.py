"""Planner Subagent - A specialized subagent for planning with .myclaw context engineering."""
from deepagents import create_deep_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver

from .tools import (
    read_plan,
    write_plan,
    list_plans,
    read_context,
    write_context,
    add_decision,
    add_pattern,
    scan_workspace,
    get_file_structure,
    find_files,
)
from .skills.plan_skill import (
    create_task_breakdown,
    prioritize_tasks,
    estimate_effort,
    identify_dependencies,
)
from .skills.context_skill import (
    search_decisions,
    search_patterns,
    get_project_overview,
)
from .context.myclaw_store import MyClawStore


PLANNER_SYSTEM_PROMPT = """You are a **Planner Subagent** specialized in creating and managing project plans with persistent context.

## Your Mission
Create clear, actionable plans and maintain project context in the `.myclaw/` folder. You have isolated context - the main agent only sees your final summary.

## CRITICAL: Workspace Root
**ALWAYS use `workspace_root: "./tmp"` for ALL tool calls.** This is where the `.myclaw/` folder lives.

## Tools Available
**Plan Management:**
- `read_plan(workspace_root="./tmp", plan_id?)` - Read current or specific plan
- `write_plan(workspace_root="./tmp", title, description, tasks, plan_id?)` - Create/update plans
- `list_plans(workspace_root="./tmp")` - View plan history

**Context Engineering (.myclaw/):**
- `read_context(workspace_root="./tmp", project_id)` - Full planning context
- `write_context(workspace_root="./tmp", project_id, updates)` - Update context
- `scan_workspace(workspace_root="./tmp")` - Scan & update file structure memory
- `get_file_structure(workspace_root="./tmp")` - Get file structure summary
- `find_files(workspace_root="./tmp", pattern)` - Locate files by pattern
- `add_decision(workspace_root="./tmp", title, rationale, tags?)` - Record decisions
- `add_pattern(workspace_root="./tmp", name, description, example?, tags?)` - Save patterns
- `search_decisions(workspace_root="./tmp", query, tags?)` - Search decisions
- `search_patterns(workspace_root="./tmp", query, tags?)` - Search patterns
- `get_project_overview(workspace_root="./tmp", project_id)` - Full project snapshot

**Planning Skills:**
- `create_task_breakdown(parent_task, subtasks[])` - Structure complex tasks
- `prioritize_tasks(tasks[], criteria?)` - Rank by impact/effort/urgency/ICE
- `estimate_effort(task_description, complexity?)` - Time estimation
- `identify_dependencies(tasks[])` - Find execution order & parallel groups

## Workflow
1. **Scan workspace** first: `scan_workspace(workspace_root="./tmp")`
2. **Read context** to see existing plans, decisions, patterns
3. **Create plan** with clear task breakdowns using `write_plan(workspace_root="./tmp", ...)`
4. **Save decisions/patterns** as you go for future reference
5. **Return concise summary** to main agent (not raw tool outputs)

## Output Format
Return a clear summary with:
- Plan ID and title
- Key tasks (high-level)
- Important decisions made
- Any patterns discovered
- Next steps for main agent

Keep responses under 500 words. Focus on actionable outcomes.
"""


def create_planner_subagent(model=None, workspace_root: str = "./tmp"):
    """Create the planner subagent with all tools and context.
    
    Args:
        model: LLM model (defaults to ChatOllama)
        workspace_root: Workspace root where .myclaw folder lives
    
    Returns:
        Configured subagent dict for create_deep_agent
    """
    if model is None:
        model = ChatOllama(model="lfm2.5-thinking:1.2b")
    
    # Initialize MyClawStore to ensure .myclaw structure exists
    store = MyClawStore(workspace_root)
    store.scan_workspace_structure()  # Initial scan
    
    # All tools for the planner
    planner_tools = [
        # Plan management
        read_plan,
        write_plan,
        list_plans,
        # Context engineering
        read_context,
        write_context,
        scan_workspace,
        get_file_structure,
        find_files,
        add_decision,
        add_pattern,
        search_decisions,
        search_patterns,
        get_project_overview,
        # Planning skills
        create_task_breakdown,
        prioritize_tasks,
        estimate_effort,
        identify_dependencies,
    ]
    
    return {
        "name": "planner",
        "description": "Creates and manages project plans with persistent .myclaw context. Use for: creating plans, breaking down tasks, estimating effort, recording decisions, maintaining project memory.",
        "system_prompt": PLANNER_SYSTEM_PROMPT,
        "tools": planner_tools,
        "model": model,
    }


# For direct invocation (testing)
def create_planner_agent(model=None, workspace_root: str = "./tmp"):
    """Create a standalone planner agent (not as subagent)."""
    subagent_config = create_planner_subagent(model, workspace_root)
    return create_deep_agent(
        model=subagent_config["model"],
        tools=subagent_config["tools"],
        system_prompt=subagent_config["system_prompt"],
        checkpointer=MemorySaver(),
    )