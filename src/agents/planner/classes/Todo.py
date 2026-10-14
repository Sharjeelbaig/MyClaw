from pydantic import BaseModel
from .Task import Task

class Todo(BaseModel):
    todo_id: str
    title: str
    description: str
    tasks: list[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)
    def remove_task(self, task: Task):
        if task in self.tasks:
            self.tasks.remove(task)
    def update_task(self, task: Task):
        for i, existing in enumerate(self.tasks):
            if existing.ticket_id == task.ticket_id:
                self.tasks[i] = task
                return