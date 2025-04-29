from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union

from rag.context_manager import Conversation, Role
from rag.rag_application import rag_query

# 存储所有活跃会话，按用户ID组织
active_sessions: Dict[int, Dict[str, Conversation]] = {}
# 存储每个会话的最后一次引用列表
session_quotes: Dict[int, Dict[str, List[str]]] = {}

router = APIRouter(prefix="/rag", tags=["RAG"])


class RagRequest(BaseModel):
    """RAG请求模型"""

    user_id: int  # 用户ID
    session_id: str  # 会话ID，-1表示新建会话
    query: str  # 用户查询内容
    top_k: int = 5  # 检索结果数量
    temperature: float = 0.7  # 温度参数


class RagResponse(BaseModel):
    """RAG响应模型"""
    id: str  # 会话ID
    conversation: List[Dict[str, Any]]  # 会话上下文
    quote: List[str]  # 引用列表


@router.post("/", response_model=RagResponse)
async def process_rag(request: RagRequest):
    """处理RAG请求"""
    user_id = request.user_id
    session_id = request.session_id
    query = request.query

    # 确保用户存在于活跃会话中
    if user_id not in active_sessions:
        active_sessions[user_id] = {}

    # 确保用户存在于引用字典中
    if user_id not in session_quotes:
        session_quotes[user_id] = {}

    # 检查是否需要创建新会话
    if session_id == "-1":
        # 创建新会话
        conversation = Conversation()
        active_sessions[user_id][conversation.id] = conversation
        session_id = conversation.id
        session_quotes[user_id][session_id] = []  # 初始化引用列表
    elif session_id not in active_sessions[user_id]:
        raise HTTPException(
            status_code=404, detail=f"用户 {user_id} 的会话ID {session_id} 不存在"
        )

    # 获取会话
    conversation = active_sessions[user_id][session_id]

    # 处理RAG查询
    try:
        result = await rag_query(
            query=query,
            conversation=conversation,
            top_k=request.top_k,
            temperature=request.temperature,
        )

        # 更新该会话的最后一次引用
        quotes = result.get("quote", [])
        session_quotes[user_id][session_id] = quotes

        # 构建响应
        response = {
            "id": session_id,
            "conversation": conversation.get_context(),
            "quote": quotes,
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理查询时出错: {str(e)}")


@router.delete("/")
async def delete_session(user_id: int, session_id: str):
    """删除指定用户的指定会话"""
    if user_id in active_sessions and session_id in active_sessions[user_id]:
        # 删除会话
        del active_sessions[user_id][session_id]

        # 同时删除对应的引用记录
        if user_id in session_quotes and session_id in session_quotes[user_id]:
            del session_quotes[user_id][session_id]

        return {
            "status": "success",
            "message": f"用户 {user_id} 的会话 {session_id} 已删除",
        }
    else:
        raise HTTPException(
            status_code=404, detail=f"用户 {user_id} 的会话ID {session_id} 不存在"
        )


@router.get("/", response_model=RagResponse)
async def get_session(user_id: int, session_id: str):
    """获取指定用户的指定会话内容"""
    if user_id in active_sessions and session_id in active_sessions[user_id]:
        conversation = active_sessions[user_id][session_id]

        # 获取会话的最后一次引用列表，如果不存在则返回空列表
        quotes = []
        if user_id in session_quotes and session_id in session_quotes[user_id]:
            quotes = session_quotes[user_id][session_id]

        return {
            "id": session_id,
            "conversation": conversation.get_context(),
            "quote": quotes,  # 返回保存的引用列表
        }
    else:
        raise HTTPException(
            status_code=404, detail=f"用户 {user_id} 的会话ID {session_id} 不存在"
        )


@router.get("/all")
async def get_user_sessions(user_id: int):
    """获取指定用户的所有会话列表"""
    if user_id not in active_sessions:
        return {"sessions": []}

    sessions = []
    for session_id, conversation in active_sessions[user_id].items():
        context = conversation.get_context()
        # 获取上下文的第一句话（查找用户角色的第一条消息）
        first_message = ""
        for message in context:
            if message.get("role") == Role.USER.value:
                first_message = message.get("content", "")
                break

        if not first_message and context:
            # 如果没有找到用户消息，就用第一条消息
            first_message = context[0].get("content", "")

        sessions.append({"id": session_id, "title": first_message})

    return {"sessions": sessions}
