import os

from deepagents import create_deep_agent, backends
from langchain_core.messages import AIMessageChunk
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from tools.python_executor import python_executor
from agents.guard import GroundingGuardMiddleware
from agents.planner.agent import create_planner_subagent
from config import WORKSPACE_ROOT

console = Console()

# The model is swappable: set AGENT_MODEL to any Ollama model/tag, e.g.
#   AGENT_MODEL=gemma4:e2b-it-qat uv run ./src/main.py
MODEL_NAME = os.getenv("AGENT_MODEL", "myclaw-lfm:latest")
WORKSPACE_MOUNT = "/workspace/"

backend = backends.CompositeBackend(
    default=backends.StateBackend(),
    routes={
        WORKSPACE_MOUNT: backends.FilesystemBackend(root_dir=str(WORKSPACE_ROOT)),
    },
)
model = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=16384,
    top_k=50,
    reasoning=True,
)

agent = create_deep_agent(
    model=model,
    checkpointer=MemorySaver(),
    backend=backend,
    tools=[
        python_executor,
    ],
    subagents=[
        create_planner_subagent(model),
    ],
    middleware=[
        GroundingGuardMiddleware(workspace_path=WORKSPACE_MOUNT),
    ],
)

config = {"configurable": {"thread_id": "user-123"}}


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(getattr(block, "text", "") or ""))
        return "".join(parts)
    return ""


def _tool_names(chunk) -> list[str]:
    names = []
    for call in getattr(chunk, "tool_call_chunks", None) or []:
        name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
        if name:
            names.append(name)
    return names


console.print(f"[dim]model: {MODEL_NAME}   (swap with AGENT_MODEL=...)[/dim]\n")

while True:
    try:
        user_input = console.input("[bold green]You:[/bold green] ")
    except (EOFError, KeyboardInterrupt):
        console.print()
        break

    buffer = ""
    used: list[str] = []
    with Live(
        Markdown(""),
        console=console,
        refresh_per_second=12,
        vertical_overflow="visible",
    ) as live:
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            stream_mode="messages",
            subgraphs=True,
            version="v2",
            config=config,
        ):
            if isinstance(chunk, dict) and chunk.get("type") == "messages":
                token, metadata = chunk["data"]
                if isinstance(token, AIMessageChunk):
                    used.extend(_tool_names(token))
                    text = _text(token.content)
                    if text:
                        buffer += text
                        live.update(Markdown(buffer))
    if used:
        console.print(f"[dim]· tools: {', '.join(dict.fromkeys(used))}[/dim]")
    console.print()
