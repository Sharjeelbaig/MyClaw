from deepagents import create_deep_agent, backends
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.markdown import Markdown
from tools.python_executor import python_executor

console = Console()
backend = backends.FilesystemBackend("./tmp")

agent = create_deep_agent(
    model=ChatOllama(model="lfm2.5-thinking:1.2b"),
    checkpointer=MemorySaver(),
    backend=backend,
    tools=[
        python_executor,
    ],
)

config = {"configurable": {"thread_id": "user-123"}}
messages = [{
    "role": "system",
    "content": """You are a helpful AI assistant with access to a Python execution tool.

You can execute Python code in two ways:
1. **File mode**: Run existing .py files in the workspace (use `mode="file", target="filename.py"`)
2. **Code mode**: Run inline Python code snippets (use `mode="code", target="print('hello')" `)

The workspace is at `./tmp/` relative to the project root. Use file mode for existing scripts, code mode for quick calculations or tests.

Always report the actual stdout/stderr from executions - never guess or invent output."""
}]

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
            