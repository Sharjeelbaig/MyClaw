from deepagents import create_deep_agent, backends
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.markdown import Markdown
from tools.python_executor import python_executor
from agents.planner import create_planner_subagent

console = Console()
backend = backends.FilesystemBackend("./tmp")
model = ChatOllama(model="gemma4:e2b")

# Create planner subagent with .myclaw context engineering
planner_subagent = create_planner_subagent(workspace_root="./tmp", model=model)

agent = create_deep_agent(
    model=model,
    checkpointer=MemorySaver(),
    backend=backend,
    tools=[
        python_executor,
    ],
    subagents=[planner_subagent],
)

config = {"configurable": {"thread_id": "user-123"}}
messages = []

while True:
    user_input = console.input("[bold green]You:[/bold green] ")
    messages.append({"role": "user", "content": user_input})
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
                print(token.content, end="", flush=True)
    print()
            