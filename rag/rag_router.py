from fastapi import APIRouter, WebSocket, HTTPException, Cookie
from typing import List
from pydantic import BaseModel
from .rag_socket import websocket_endpoint
from rag.utils.session import (
    get_user_sessions,
    get_session_messages,
    delete_session,
    get_session,
)
from access_token import get_user_id

router = APIRouter(prefix="/chat", tags=["RagChat"])


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
                    require="picture",
                ),
                FeatureOperation(
                    name="游戏存档分析", icon="operations/savefile.png", require="file"
                ),
            ],
        ),
        RAGInstance(
            id="op",
            name="原神助手",
            description="启动一下",
            initial_message="这是什么？启动一下。",
            operations=[],
        ),
    ]

    return {"assistants": assistants}


@router.websocket("/ws/{token}")
async def websocket_route(websocket: WebSocket, token: str):
    """WebSocket连接"""
    try:
        client_id = await get_user_id(token)
        await websocket_endpoint(websocket, str(client_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{category}")
async def get_sessions(category: str, access_token: str = Cookie(None)):
    """获取用户在特定助手下的所有会话"""
    try:
        user_id = await get_user_id(access_token)
        sessions = get_user_sessions(user_id, category)
        return [
            ChatSessionResponse(
                id=session.id,
                category=session.category,
                summary=session.summary,
                updated=session.updated,
            )
            for session in sessions
        ]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/{session_id}")
async def get_messages(session_id: int, access_token: str = Cookie(None)):
    """获取特定会话的所有消息"""
    try:
        user_id = await get_user_id(access_token)
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not allowed.")
        messages = get_session_messages(session_id)
        return [
            ChatMessageResponse(
                id=message.id,
                type=message.type,
                content=message.content,
                feature=message.feature,
            )
            for message in messages
        ]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: int, access_token: str = Cookie(None)):
    """删除特定会话及其所有消息"""
    try:
        user_id = await get_user_id(access_token)
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not allowed.")

        success = delete_session(session_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
