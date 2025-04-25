from typing import List, Literal, Optional
from pydantic import BaseModel


class AddTaskRequest(BaseModel):
    name: str
    task_id: Optional[int | None] = None
    methods: List[str]
    category: Literal["rag", "prompt"]
    input_ids: Optional[List[int]] = None
    input_texts: Optional[List[str]] = None


class AlterTaskRequest(BaseModel):
    task_id: int
    name: str
    method: str


class GetFileInfoRequest(BaseModel):
    category: Literal["input", "output"]
    file_ids: List[int]


class CreatePlotRequest(BaseModel):
    task_id: int
    method: str
