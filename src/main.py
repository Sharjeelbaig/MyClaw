from deepagents import create_deep_agent, backends
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.markdown import Markdown
from tools.python_executor import python_executor
from planning import create_planner_subagent

console = Console()
backend = backends.FilesystemBackend("./tmp")

# Create planner subagent with .myclaw context engineering
planner_subagent = create_planner_subagent(workspace_root="./tmp")

agent = create_deep_agent(
    model=ChatOllama(model="granite4:latest"),
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
    # result = agent.invoke({
    #     "messages": messages
    # }, config=config)

    # output = Markdown(result["messages"][-1].content)
    # messages.append({"role": "assistant", "content": result["messages"][-1].content})
    # console.print(output)
    for chunk in agent.stream(
        {"messages": messages},
        stream_mode="messages",
        subgraphs=True,
        version="v2",
        config=config
    ):
        # chunk is a dict: {"type": "messages", "data": (token, metadata), "ns": [...]}
        if isinstance(chunk, dict) and chunk.get("type") == "messages":
            token, metadata = chunk["data"]
            if hasattr(token, 'content') and token.content:
                print(token.content, end="", flush=True)
    print()  # newline after streaming completes
            