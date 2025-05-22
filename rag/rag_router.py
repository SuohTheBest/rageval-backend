from fastapi import APIRouter, WebSocket
from typing import List
from pydantic import BaseModel
from .rag_socket import websocket_endpoint
from .utils import get_user_sessions, get_session_messages

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


class ChatSessionResponse(BaseModel):
    id: int
    category: str
    summary: str
    updated: int


class ChatMessageResponse(BaseModel):
    id: int
    type: str
    content: str
    feature: str | None = None


@router.get("/assistants")
async def get_assistants():
    """获取所有可用的RAG助手列表"""
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
async def websocket_route(websocket: WebSocket, client_id: int):
    await websocket_endpoint(websocket, str(client_id))


@router.get("/sessions/{user_id}/{category}")
async def get_sessions(user_id: int, category: str):
    """获取用户在特定助手下的所有会话"""
    sessions = get_user_sessions(user_id, category)
    return [ChatSessionResponse(
        id=session.id,
        category=session.category,
        summary=session.summary,
        updated=session.updated
    ) for session in sessions]


@router.get("/messages/{session_id}")
async def get_messages(session_id: int):
    """获取特定会话的所有消息"""
    messages = get_session_messages(session_id)
    return [ChatMessageResponse(
        id=message.id,
        type=message.type,
        content=message.content,
        feature=message.feature
    ) for message in messages]


