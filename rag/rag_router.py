from fastapi import APIRouter, HTTPException, WebSocket
from typing import List
from pydantic import BaseModel
from .rag_socket import websocket_endpoint

router = APIRouter(prefix='/chat', tags=['RagChat'])


class FeatureOperation(BaseModel):
    name: str
    icon: str | None = None
    require: str = "none"  # none, picture, file


class RAGInstance(BaseModel):
    id: str
    name: str
    icon: str | None = None
    description: str
    initial_message: str
    operations: List[FeatureOperation]


@router.get("/assistants")
async def get_assistants():
    # 获取所有可用的RAG助手列表
    assistants = [
        RAGInstance(
            id="terraria",
            name="🗡️🌳✨泰拉瑞亚助手🗡️🌳✨",
            description="专门解答泰拉瑞亚游戏相关问题的AI助手，包括武器数据、敌怪机制、Boss攻略等",
            initial_message="你好，我是泰拉瑞亚助手，精通武器数据、敌怪机制以及Boss攻略。让我们开始对话吧！",
            icon="assistants/terraria.png",
            operations=[
                FeatureOperation(
                    name="游戏截图上传",
                    icon="operations/picture.svg",
                    require="picture"
                ),
                FeatureOperation(
                    name="游戏存档分析",
                    icon="operations/savefile.png",
                    require="file"
                ),
            ]
        ),
        RAGInstance(
            id="op",
            name="原神助手",
            description="启动一下",
            initial_message="这是什么？启动一下。",
            operations=[]
        )
    ]

    return {"assistants": assistants}


@router.websocket("/ws/{client_id}")
async def websocket_route(websocket: WebSocket, client_id: str):
    await websocket_endpoint(websocket, client_id)


