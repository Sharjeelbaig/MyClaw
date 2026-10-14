# Creating a subagent

A **subagent** is a smaller, focused agent that the main agent can delegate to.
Every subagent lives in its own folder and has the **same shape**, so creating one
is mostly mechanical.

> Rule: subagents are self-contained. A subagent never imports another subagent.
> If two agents need the same code, move that code somewhere shared instead.

## 1. Run the scaffolder

From the project root:

```bash
uv run python scripts/new_agent.py
```

It asks a few questions:

| Prompt | Example | Notes |
|---|---|---|
| Agent name | `weather` | lowercase `snake_case`; becomes the folder name |
| Description | `Looks up weather for a city.` | the main agent reads this to decide when to delegate |
| System prompt | *(press Enter to accept the default)* | the agent's instructions |
| Tools | `getWeather, getForecast` | comma separated; each becomes an empty tool file |

The script **never overwrites** an existing agent folder — if the folder is there,
it asks again for the name.

## 2. What it creates

```
src/agents/weather/
├─ __init__.py
├─ agent.py          # create_weather_subagent(model) -> dict
├─ prompt.py         # SYSTEM_PROMPT
├─ tools/
│  ├─ __init__.py
│  ├─ get_weather.py
│  └─ get_forecast.py
└─ classes/
   └─ __init__.py
```

- `agent.py` wires the agent together (name, description, prompt, tools, model).
- `prompt.py` holds the system prompt as a single `SYSTEM_PROMPT` string.
- `tools/` holds one file per tool.
- `classes/` is where this agent's Pydantic models go.

## 3. Code the tools

Each tool file starts as a stub:

```python
from langchain.tools import tool, ToolRuntime

@tool
def getWeather(runtime: ToolRuntime) -> str:
    """TODO: describe what this tool does and when the model should call it."""
    pass
```

Replace `pass` with the real logic. The **docstring matters** — that is what the
model reads to decide when to call the tool, so describe it clearly.

`runtime` is special: it is **injected automatically** and is *not* something the
model supplies. Only the other parameters are filled by the model.

Example:

```python
from langchain.tools import tool, ToolRuntime

@tool
def getWeather(city: str, runtime: ToolRuntime) -> str:
    """Return the current weather for a city."""
    return f"It is sunny in {city}."
```

> Keep the function name in `camelCase` (e.g. `getWeather`) and the file name in
> `snake_case` (e.g. `get_weather.py`). The scaffolder already does this for you.

## 4. Add models or storage (optional)

- Put Pydantic models the agent needs in `classes/`.
- If the agent saves data to disk, add a `store.py` next to `agent.py` for the
  load/save helpers. See `src/agents/planner/store.py` for a working example.

## 5. Wire it into the main agent

In `src/main.py`, import the factory and add it to `subagents`:

```python
from agents.planner.agent import create_planner_subagent
from agents.weather.agent import create_weather_subagent

agent = create_deep_agent(
    model=model,
    checkpointer=MemorySaver(),
    backend=backend,
    tools=[python_executor],
    subagents=[
        create_planner_subagent(model),
        create_weather_subagent(model),
    ],
)
```

## 6. Test

Run the app and ask something that needs the new agent. Confirm the main agent
delegates to it.

## Structure reference

| Thing | Convention | Example |
|---|---|---|
| Folder (agent name) | `snake_case` | `weather` |
| Factory | `create_<name>_subagent(model) -> dict` | `create_weather_subagent` |
| Prompt | `SYSTEM_PROMPT` in `prompt.py` | |
| Tool function | `camelCase` | `getWeather` |
| Tool file | `snake_case` of the function | `get_weather.py` |
| Model class | `PascalCase.py` in `classes/` | `Todo.py` |
