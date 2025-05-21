from models.rag_chat import ChatSession, ChatMessage
from models.database import SessionLocal
import time
from typing import List, Optional


def create_session(user_id: int, assistant_id: str) -> ChatSession:
    """创建会话"""
    db = SessionLocal()
    try:
        session = ChatSession(
            user_id=user_id,
            category=assistant_id,
            summary="新会话",
            updated=int(time.time())
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    finally:
        db.close()


def get_session(session_id: int) -> Optional[ChatSession]:
    """获取指定会话"""
    db = SessionLocal()
    try:
        return db.query(ChatSession).filter(ChatSession.id == session_id).first()
    finally:
        db.close()


def save_message(session_id: int, type: str, content: str, feature: str = None) -> ChatMessage:
    """保存消息到数据库"""
    db = SessionLocal()
    try:
        message = ChatMessage(
            session_id=session_id,
            type=type,
            content=content,
            feature=feature
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    finally:
        db.close()


def update_session_summary(session_id: int, summary: str):
    """更新会话摘要"""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.summary = summary
            session.updated = int(time.time())
            db.commit()
    finally:
        db.close()


def get_user_sessions(user_id: int, category: str) -> List[ChatSession]:
    """获取用户在特定助手下的所有会话"""
    db = SessionLocal()
    try:
        return db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.category == category
        ).order_by(ChatSession.updated.desc()).all()
    finally:
        db.close()


def get_session_messages(session_id: int) -> List[ChatMessage]:
    """获取特定会话的所有消息"""
    db = SessionLocal()
    try:
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.id.asc()).all()
    finally:
        db.close()
