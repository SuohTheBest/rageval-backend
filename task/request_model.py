from typing import List, Literal, Optional

from fastapi import Query
from pydantic import BaseModel


class AddTaskRequest(BaseModel):
    name: str
    task_id: Optional[int | None] = None
    methods: List[str]
    category: Literal["rag", "prompt"]
    input_ids: Optional[List[int]] = None
    input_texts: Optional[List[str]] = None
    autofill: Optional[str] = 'none'
    user_fill: Optional[str] = None  # 用户自己的填充
    custom_method_ids: Optional[List[int]] = None  # 自定义指标的ID列表


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


class DeleteTaskRequest(BaseModel):
    task_id: int
    eval_ids: List[int] = Query(None)


class AddMetricRequest(BaseModel):
    name: str
    category: Literal["rag", "prompt"]
    description: str


class UpdateMetricRequest(BaseModel):
    id: int
    name: str
    description: str
