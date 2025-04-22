from sqlalchemy import Column, Integer, Text
from models.database import Base


class RAGText(Base):
    __tablename__ = "text"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text)
