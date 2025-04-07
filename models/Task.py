import time

from sqlalchemy import Column, String, Integer, Index

from database import Base


class Task(Base):
    __tablename__ = 'task'
    __table_args__ = (
        Index('ix_user_id', 'user_id'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    input_id = Column(String(32))  # 输入和输出，采用文件形式
    output_id = Column(String(32))
    name = Column(String(32))
    method = Column(String(16))
    status = Column(String(16))
    created = Column(Integer, default=int(time.time()))

    def __repr__(self):
        return ("<Task(name='%s', method='%s', status='%s', created='%d')>"
                % (self.name, self.method, self.status, self.created))
