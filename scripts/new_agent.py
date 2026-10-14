#!/usr/bin/env python3
"""Scaffold a new subagent.

Usage:
    uv run python scripts/new_agent.py

Creates src/agents/<name>/ with a boilerplate agent, a prompt file, and one
empty tool file per tool name you provide. Existing folders are never
overwritten.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "src" / "agents"

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def camel_to_snake(name: str) -> str:
    """createOrUpdateTodo -> create_or_update_todo"""
    step1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    step2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step1)
    return step2.lower()


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_name() -> str:
    while True:
        name = ask("Agent name (snake_case, e.g. weather)")
        if not NAME_RE.match(name):
            print("  ! lowercase letters/digits/underscores only, start with a letter")
            continue
        if (AGENTS_DIR / name).exists():
            print(f"  ! src/agents/{name} already exists")
            continue
        return name


def ask_description() -> str:
    while True:
        description = ask("Description (the orchestrator reads this to pick the agent)")
        if description:
            return description
        print("  ! description is required")


def ask_tools() -> list[str]:
    while True:
        raw = ask("Tools (comma separated, e.g. getWeather, getForecast)")
        if not raw:
            return []
        names = [t.strip() for t in raw.split(",") if t.strip()]
        bad = [t for t in names if not IDENT_RE.match(t)]
        if bad:
            print(f"  ! not valid Python names: {', '.join(bad)}")
            continue
        seen: set[str] = set()
        unique: list[str] = []
        for t in names:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique


def prompt_source(system_prompt: str) -> str:
    safe = system_prompt.replace('"""', '\\"\\"\\"')
    return f'SYSTEM_PROMPT = """{safe}"""\n'


def agent_source(name: str, description: str, tools: list[str]) -> str:
    lines = [f"from agents.{name}.prompt import SYSTEM_PROMPT"]
    for tool in tools:
        lines.append(f"from agents.{name}.tools.{camel_to_snake(tool)} import {tool}")
    lines += [
        "",
        "",
        f"def create_{name}_subagent(model) -> dict:",
        "    return {",
        f'        "name": {json.dumps(name)},',
        f'        "description": {json.dumps(description)},',
        '        "system_prompt": SYSTEM_PROMPT,',
        f'        "tools": [{", ".join(tools)}],',
        '        "model": model,',
        "    }",
        "",
    ]
    return "\n".join(lines)


def tool_source(tool_name: str) -> str:
    return (
        "from langchain.tools import tool, ToolRuntime\n"
        "\n"
        "\n"
        "@tool\n"
        f"def {tool_name}(runtime: ToolRuntime) -> str:\n"
        '    """TODO: describe what this tool does and when the model should call it."""\n'
        "    pass\n"
    )


def main() -> int:
    print("== New subagent ==\n")

    name = ask_name()
    description = ask_description()
    default_prompt = f"You are the {name} agent. {description}"
    system_prompt = ask("System prompt", default=default_prompt)
    tools = ask_tools()

    agent_dir = AGENTS_DIR / name
    tools_dir = agent_dir / "tools"
    classes_dir = agent_dir / "classes"

    tools_dir.mkdir(parents=True)
    classes_dir.mkdir(parents=True)

    (agent_dir / "__init__.py").write_text("")
    (classes_dir / "__init__.py").write_text("")
    (tools_dir / "__init__.py").write_text("")
    (agent_dir / "prompt.py").write_text(prompt_source(system_prompt))
    (agent_dir / "agent.py").write_text(agent_source(name, description, tools))
    for tool in tools:
        (tools_dir / f"{camel_to_snake(tool)}.py").write_text(tool_source(tool))

    print(f"\nCreated src/agents/{name}/\n")
    for path in sorted(agent_dir.rglob("*.py")):
        print(f"  {path.relative_to(ROOT)}")

    print("\nNext steps:")
    print(f"  1. Fill in the tool bodies in src/agents/{name}/tools/")
    print("  2. Wire it into src/main.py:")
    print(f"       from agents.{name}.agent import create_{name}_subagent")
    print(f"       subagents=[..., create_{name}_subagent(model)]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
