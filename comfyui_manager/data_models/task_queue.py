"""
Task queue data models for ComfyUI Manager.

Contains Pydantic models for task queue management, WebSocket messaging,
and task state tracking.
"""

from typing import Optional, Union, Dict
from enum import Enum
from pydantic import BaseModel


class QueueTaskItem(BaseModel):
    """Represents a task item in the queue."""

    ui_id: str
    client_id: str
    kind: str


class TaskHistoryItem(BaseModel):
    """Represents a completed task in the history."""

    ui_id: str
    client_id: str
    kind: str
    timestamp: str
    result: str
    status: Optional[dict] = None


class TaskStateMessage(BaseModel):
    """Current state of the task queue system."""

    history: Dict[str, TaskHistoryItem]
    running_queue: list[QueueTaskItem]
    pending_queue: list[QueueTaskItem]


class MessageTaskDone(BaseModel):
    """WebSocket message sent when a task completes."""

    ui_id: str
    result: str
    kind: str
    status: Optional[dict]
    timestamp: str
    state: TaskStateMessage


class MessageTaskStarted(BaseModel):
    """WebSocket message sent when a task starts."""

    ui_id: str
    kind: str
    timestamp: str
    state: TaskStateMessage


# Union type for all possible WebSocket message updates
MessageUpdate = Union[MessageTaskDone, MessageTaskStarted]


class ManagerMessageName(Enum):
    """WebSocket message type constants."""

    TASK_DONE = "cm-task-completed"
    TASK_STARTED = "cm-task-started"
    STATUS = "cm-queue-status"
