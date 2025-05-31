from fastapi import APIRouter, WebSocket, HTTPException, Cookie, UploadFile, File, Form
from typing import List

from fastapi.params import Query
from pydantic import BaseModel
from .rag_socket import websocket_endpoint, temp_files
from rag.utils.chat_session import (
    get_user_sessions,
    get_session_messages,
    delete_session,
    get_session,
    get_message_metadata,
    check_admin,
    add_knowledge_base,
    delete_knowledge_base,
    get_knowledge_bases,
    get_knowledge_base,
)
from access_token import get_user_id
import os
import uuid
import time

router = APIRouter(prefix="/chat", tags=["RagChat"])


class FeatureOperation(BaseModel):
    name: str
    icon: str | None = None
    require: str = "none"  # none, picture, file
    url: str | None = None


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
    metadata: dict | List[dict] | None = None


class KnowledgeBaseRequest(BaseModel):
    assistant_id: str
    name: str
    path: str
    description: str


class KnowledgeBaseResponse(BaseModel):
    id: int
    assistant_id: str
    name: str
    path: str
    description: str


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
                    name="游戏存档分析", icon="operations/file.svg", require="file"
                ),
                FeatureOperation(
                    name="合成树查询", icon="operations/search.svg", require="web", url="/terraria/search"
                )
            ],
        ),
        RAGInstance(
            id="gok",
            name="🗡️🗡️🗡️王者荣耀助手🗡️🗡️🗡️",
            description="专门解答王者荣耀游戏相关问题的AI助手，包括英雄数据、装备推荐、战术分析等",
            initial_message="你好，我是王者荣耀助手，精通英雄数据、装备推荐以及战术分析。让我们开始对话吧！",
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
                metadata=get_message_metadata(message),
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


@router.post("/temp_file")
async def upload_temp_file(
        file: UploadFile = File(...), access_token: str = Cookie(None)
):
    """上传临时文件"""
    try:
        user_id = await get_user_id(access_token)
        temp_file_id = str(uuid.uuid4())
        file_type = "picture" if file.content_type.startswith("image/") else "file"
        temp_dir = os.path.join("uploads", "temp", str(user_id))
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        file_size = 0
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):
                f.write(chunk)
                file_size += len(chunk)

        meta = {
            "file_path": file_path,
            "file_name": file.filename,
            "file_size": file_size,
            "file_type": file_type,
        }
        temp_files[temp_file_id] = meta
        return {"temp_file_id": temp_file_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge_base")
async def add_knowledge_base_route(
        file: UploadFile = File(...),
        type: str = Form(...),
        description: str = Form(...),
        assistant_id: str = Form(...),
        access_token: str = Cookie(None),
):
    """添加知识库"""
    try:
        user_id = await get_user_id(access_token)
        if not check_admin(user_id):
            raise HTTPException(status_code=403, detail="需要管理员权限")
        # 创建知识库目录
        kb_dir = os.path.join("data", "knowledge_library")
        os.makedirs(kb_dir, exist_ok=True)

        # 生成文件名
        file_name = os.path.splitext(file.filename)[0]
        file_path = os.path.join(kb_dir, file.filename)

        # 保存文件
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):
                f.write(chunk)

        # 添加到数据库
        kb = add_knowledge_base(
            name=file_name,
            path=file_path,
            description=description,
            assistant_id=assistant_id,
            type=type,
            created_at=int(time.time()),
        )

        return {
            "id": kb.id,
            "name": kb.name,
            "path": kb.path,
            "description": kb.description,
            "assistant_id": kb.assistant_id,
            "type": kb.type,
            "created_at": kb.created_at,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge_base")
async def get_knowledge_bases_route(assistant_id: str = Query(...)):
    """获取所有知识库"""
    try:
        kbs = get_knowledge_bases(assistant_id)
        return [
            {
                "id": kb.id,
                "name": kb.name,
                "path": kb.path,
                "description": kb.description,
                "type": kb.type,
                "created_at": kb.created_at,
            }
            for kb in kbs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge_base/{kb_id}")
async def delete_knowledge_base_route(kb_id: int, access_token: str = Cookie(None)):
    """删除知识库"""
    try:
        user_id = await get_user_id(access_token)
        if not check_admin(user_id):
            raise HTTPException(status_code=403, detail="需要管理员权限")
        # 获取知识库信息
        kb = get_knowledge_base(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        # 删除文件
        if os.path.exists(kb.path):
            os.remove(kb.path)
        # 删除数据库记录
        if not delete_knowledge_base(kb_id):
            raise HTTPException(status_code=404, detail="知识库不存在")
        return {"success": True}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
