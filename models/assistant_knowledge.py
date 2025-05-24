from sqlalchemy import Column, String, Index
from models.database import Base


class AssistantKnowledgeBase(Base):
    """助手-知识库关联表"""

    __tablename__ = "assistant_knowledge_base"
    __table_args__ = (
        Index("ix_assistant_knowledge_base_assistant_id", "assistant_id"),
        Index("ix_assistant_knowledge_base_knowledge_base_name", "knowledge_base_name"),
    )

    assistant_id = Column(String, primary_key=True)
    knowledge_base_name = Column(String, primary_key=True)

    def __repr__(self):
        return f"<AssistantKnowledgeBase(assistant_id='{self.assistant_id}', knowledge_base_name='{self.knowledge_base_name}')>"
