from pydantic import BaseModel
from typing import Literal

class Task(BaseModel):
    ticket_id: str
    title: str
    description: str
    status: Literal["todo", "in_progress", "done"] = "todo"