from deepagents import create_deep_agent, backends
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.markdown import Markdown
from tools.docker import docker

console = Console()
backend = backends.FilesystemBackend("./tmp")

agent = create_deep_agent(
    model=ChatOllama(model="granite4:latest"),
    checkpointer=MemorySaver(),
    backend=backend,
    tools=[
        docker,
    ]
)

config = {"configurable": {"thread_id": "user-123"}}
messages = [{"role": "system", "content": "Greet the user."}]

while True:
    user_input = console.input("[bold green]You:[/bold green] ")
    messages.append({"role": "user", "content": user_input})
    result = agent.invoke({
        "messages": messages
    }, config=config)

    output = Markdown(result["messages"][-1].content)
    messages.append({"role": "assistant", "content": result["messages"][-1].content})
    console.print(output)