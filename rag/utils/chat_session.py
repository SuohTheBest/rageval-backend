from models.rag_chat import (
    ChatSession,
    ChatMessage,
    RetrievalSource,
    FileOrPictureSource,
    KnowledgeBase,
)
from models.database import SessionLocal
import time
from typing import List, Optional
import os
import shutil
import asyncio
from models.User import User
from rag.application.knowledge_manager import KnowledgeManager

knowledge_manager = KnowledgeManager()


def create_session(user_id: int, assistant_id: str) -> ChatSession:
    """创建会话"""
    db = SessionLocal()
    try:
        session = ChatSession(
            user_id=user_id,
            category=assistant_id,
            summary="新会话",
            updated=int(time.time()),
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


def save_message(
        session_id: int, role: str, content: str, feature: str = None
) -> ChatMessage:
    """保存消息到数据库"""
    db = SessionLocal()
    try:
        message = ChatMessage(
            session_id=session_id, type=role, content=content, feature=feature
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
        return (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id, ChatSession.category == category)
            .order_by(ChatSession.updated.desc())
            .all()
        )
    finally:
        db.close()


def get_session_messages(session_id: int) -> List[ChatMessage]:
    """获取特定会话的所有消息"""
    db = SessionLocal()
    try:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
    finally:
        db.close()


def delete_session(session_id: int) -> bool:
    """删除指定会话及其所有消息"""
    db = SessionLocal()
    try:
        messages = (
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()
        )

        retrieval_message_ids = []
        file_picture_message_ids = []

        for msg in messages:
            if msg.meta_type == "retrieval":
                retrieval_message_ids.append(msg.id)
            elif msg.meta_type in ["file", "picture"]:
                file_picture_message_ids.append(msg.id)

        if retrieval_message_ids:
            db.query(RetrievalSource).filter(
                RetrievalSource.message_id.in_(retrieval_message_ids)
            ).delete()

        if file_picture_message_ids:
            # 获取所有文件记录
            file_sources = (
                db.query(FileOrPictureSource)
                .filter(FileOrPictureSource.message_id.in_(file_picture_message_ids))
                .all()
            )

            # 删除文件
            for source in file_sources:
                if source.path and os.path.exists(source.path):
                    try:
                        os.remove(source.path)
                    except Exception as e:
                        print(f"删除文件失败: {source.path}, 错误: {str(e)}")

            # 删除数据库记录
            db.query(FileOrPictureSource).filter(
                FileOrPictureSource.message_id.in_(file_picture_message_ids)
            ).delete()

        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()

        result = db.query(ChatSession).filter(ChatSession.id == session_id).delete()
        db.commit()
        return result > 0
    finally:
        db.close()


def save_message_with_temp_file(
        session_id: int,
        role: str,
        content: str = None,
        feature: str = None,
        temp_file_id: str = None,
        temp_files: dict = None,
) -> tuple[ChatMessage, FileOrPictureSource]:
    """保存消息和关联的临时文件到数据库"""
    db = SessionLocal()
    try:
        # 保存消息
        message = ChatMessage(
            session_id=session_id,
            type=role,
            content=content,
            feature=feature,
            meta_type="none",
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        file_source = None
        # 如果有临时文件，处理文件
        if temp_file_id and temp_file_id in temp_files:
            temp_file = temp_files[temp_file_id]
            file_type = temp_file["file_type"]
            name, ext = os.path.splitext(temp_file["file_name"])
            # 创建目标目录
            target_dir = os.path.join("uploads", file_type)
            os.makedirs(target_dir, exist_ok=True)
            # 移动文件
            target_path = os.path.join(
                target_dir, (temp_file_id + name)[:40] + ext
            )
            shutil.move(temp_file["file_path"], target_path)

            # 创建文件记录
            file_source = FileOrPictureSource(
                message_id=message.id,
                title=temp_file["file_name"],
                size=temp_file["file_size"],
                path=target_path,
                type=file_type,
            )
            # 更新消息的meta_type
            message.meta_type = temp_file["file_type"]
            db.add(file_source)
            db.commit()
            # 删除临时文件记录
            del temp_files[temp_file_id]
        return message, file_source
    finally:
        db.close()


def save_assistant_message(
        session_id: int, content: str, retrieval: List[RetrievalSource]
) -> ChatMessage:
    """保存消息到数据库"""
    db = SessionLocal()
    try:
        message = ChatMessage(
            session_id=session_id,
            type="assistant",
            content=content,
            feature="retrieval",
        )
        db.add(message)
        for source in retrieval:
            db.add(source)
        db.commit()
        db.refresh(message)
        return message
    finally:
        db.close()


def get_message_metadata(message: ChatMessage):
    """获取消息的元数据"""
    if not message.meta_type or message.meta_type == "none":
        return None
    db = SessionLocal()
    try:
        metadata = {}
        if message.meta_type == "retrieval":
            sources = (
                db.query(RetrievalSource)
                .filter(RetrievalSource.message_id == message.id)
                .first()
            )
            if sources:
                metadata["sources"] = [
                    {
                        "title": source.title,
                        "url": source.url,
                        "snippet": source.snippet,
                        "similarityScore": source.similarity_score,
                    }
                    for source in sources
                ]
        elif message.meta_type in ["file", "picture"]:
            source = (
                db.query(FileOrPictureSource)
                .filter(FileOrPictureSource.message_id == message.id)
                .first()
            )
            if source:
                metadata["sources"] = {
                    "id": source.id,
                    "title": source.title,
                    "size": source.size,
                    "type": source.type,
                }

        return metadata if metadata else None
    finally:
        db.close()


def check_admin(user_id: int) -> bool:
    """检查用户是否是管理员"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user and user.role == "admin"
    finally:
        db.close()


def add_knowledge_base(
        name: str,
        path: str,
        description: str,
        type: str,
        assistant_id: str,
        created_at: int,
) -> KnowledgeBase:
    """添加知识库"""
    db = SessionLocal()
    try:
        kb = KnowledgeBase(
            name=name,
            path=path,
            description=description,
            assistant_id=assistant_id,
            type=type,
            created_at=created_at,
        )
        asyncio.run(knowledge_manager.add_knowledge(kb))
        db.add(kb)
        db.commit()
        db.refresh(kb)
        return kb
    finally:
        db.close()


def get_knowledge_base(kb_id: int) -> Optional[KnowledgeBase]:
    """获取知识库信息"""
    db = SessionLocal()
    try:
        return db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    finally:
        db.close()


def delete_knowledge_base(kb_id: int) -> bool:
    """删除知识库"""
    db = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return False
        asyncio.run(knowledge_manager.delete_knowledge(kb))
        db.delete(kb)
        db.commit()
        return True
    finally:
        db.close()


def get_knowledge_bases() -> List[KnowledgeBase]:
    """获取所有知识库"""
    db = SessionLocal()
    try:
        asyncio.run(knowledge_manager._sync_library())
        return db.query(KnowledgeBase).all()
    finally:
        db.close()
