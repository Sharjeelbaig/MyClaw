from deepagents import create_deep_agent, backends
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from tools.python_executor import python_executor
from agents.planner.agent import create_planner_subagent
from config import WORKSPACE_ROOT

console = Console()
backend = backends.CompositeBackend(
    default=backends.StateBackend(),
    routes={
        "/workspace/": backends.FilesystemBackend(root_dir=str(WORKSPACE_ROOT)),
    },
)
model = ChatOllama(model="gemma4:e2b")

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
)

config = {"configurable": {"thread_id": "user-123"}}
messages = []

while True:
    user_input = console.input("[bold green]You:[/bold green] ")
    messages.append({"role": "user", "content": user_input})

    buffer = ""
    with Live(
        Markdown(""),
        console=console,
        refresh_per_second=12,
        vertical_overflow="visible",
    ) as live:
        for chunk in agent.stream(
            {"messages": messages},
            stream_mode="messages",
            subgraphs=True,
            version="v2",
            config=config
        ):
            if isinstance(chunk, dict) and chunk.get("type") == "messages":
                token, metadata = chunk["data"]
                if hasattr(token, 'content') and token.content:
                    buffer += token.content
                    live.update(Markdown(buffer))
    console.print()
            