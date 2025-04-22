from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import uvicorn
import uuid

from context_manager import Conversation, Role
from rag_application import rag_query

app = FastAPI(title="RAG API", description="检索增强生成API")

# 存储所有活跃会话
active_sessions: Dict[str, Conversation] = {}


class RagRequest(BaseModel):
    """RAG请求模型"""

    session_id: str  # 会话ID，-1表示新建会话
    query: str  # 用户查询内容
    top_k: int = 5  # 检索结果数量
    use_custom_prompt: bool = False  # 是否使用自定义提示
    temperature: float = 0.7  # 温度参数


class RagResponse(BaseModel):
    """RAG响应模型"""

    id: str  # 会话ID
    conversation: List[Dict[str, Any]]  # 会话上下文
    quote: List[str]  # 引用列表


@app.post("/rag", response_model=RagResponse)
async def process_rag(request: RagRequest):
    """处理RAG请求"""
    session_id = request.session_id
    query = request.query

    # 检查是否需要创建新会话
    if session_id == "-1":
        # 创建新会话
        conversation = Conversation()
        active_sessions[conversation.id] = conversation
    elif session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")

    # 获取会话
    conversation = active_sessions[session_id]

    # 处理RAG查询
    try:
        result = rag_query(
            query=query,
            conversation=conversation,
            top_k=request.top_k,
            use_custom_prompt=request.use_custom_prompt,
            temperature=request.temperature,
        )

        # 构建响应
        response = {
            "id": session_id,
            "conversation": conversation.get_context(),
            "quote": result.get("quote", []),
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理查询时出错: {str(e)}")


@app.delete("/rag/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"status": "success", "message": f"会话 {session_id} 已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"会话ID {session_id} 不存在")


# 用于直接运行 (python rag.py)
if __name__ == "__main__":
    uvicorn.run("rag:app", host="0.0.0.0", port=8000, reload=True)
