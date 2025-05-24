from sqlalchemy import Column, Integer, String, Index, Float

from models.database import Base


class ChatSession(Base):
    __tablename__ = "chat_session"
    __table_args__ = (Index("ix_chat_session_user_id", "user_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    category = Column(String(32))  # Rag实例id
    summary = Column(String(255))  # 总结
    updated = Column(Integer)

    def __repr__(self):
        return "<ChatSession(id='%s', category='%s', summary='%s')>" % (
            self.id,
            self.category,
            self.summary,
        )


class ChatMessage(Base):
    __tablename__ = "chat_message"
    __table_args__ = (Index("ix_chat_message_session_id", "session_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer)
    type = Column(String(16))  # user, assistant, system
    feature = Column(String)  # 特殊技能
    content = Column(String)
    meta_type = Column(String(16))  # 元数据类型, "retrieval", "file", "picture", "none"


# 仅限assistant
class RetrievalSource(Base):
    __tablename__ = "retrieval_source"
    __table_args__ = (Index("ix_retrieval_message_id", "message_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer)
    title = Column(String)
    url = Column(String)
    snippet = Column(String)
    similarity_score = Column(Float)


# 仅限user
class FileOrPictureSource(Base):
    __tablename__ = "file_or_picture_source"
    __table_args__ = (Index("ix_file_or_picture_source_message_id", "message_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer)
    title = Column(String)
    size = Column(Integer)
    type = Column(String(16))  # "file", "picture"
