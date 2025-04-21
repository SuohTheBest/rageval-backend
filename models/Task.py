import time

from sqlalchemy import Column, String, Integer, Index

from models.database import Base


class Task(Base):
    __tablename__ = "task"
    __table_args__ = (Index("ix_user_id", "user_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    input_id = Column(Integer)  # 输入和输出，采用文件形式
    output_id = Column(Integer)
    name = Column(String(32))
    method = Column(String(16))
    category = Column(String(16))  # rag, prompt
    status = Column(String(16))  # waiting, evaluating, success, failed
    message = Column(String(128))
    created = Column(Integer)
    started = Column(Integer)
    finished = Column(Integer)

    def __repr__(self):
        return "<Task(name='%s', method='%s', status='%s', created='%d')>" % (
            self.name,
            self.method,
            self.status,
            self.created,
        )


class UploadFile(Base):
    __tablename__ = "upload_file"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    file_name = Column(String(32))
    size: int = Column(Integer)


class DownloadFile(Base):
    __tablename__ = "download_file"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    file_name = Column(String(32))
    size: int = Column(Integer)
