import time

from sqlalchemy import Column, String, Integer, Index, Boolean

from models.database import Base


class Task(Base):
    __tablename__ = "task"
    __table_args__ = (Index("ix_user_id", "user_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    name = Column(String(32))
    category = Column(String(16))  # rag, prompt

    def __repr__(self):
        return "<Task(id='%s', name='%s', category='%s')>" % (
            self.id,
            self.name,
            self.category,
        )


class RAGEvaluation(Base):
    __tablename__ = "rag_evaluation"
    __table_args__ = (Index("ix_rag_task_id", "task_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer)
    abstract = Column(String(16))
    method = Column(String(32))
    input_id = Column(Integer)
    input_text = Column(String)
    output_id = Column(Integer)
    output_text = Column(String)
    status = Column(String(16))  # waiting, evaluating, success, failed
    created = Column(Integer)
    started = Column(Integer)
    finished = Column(Integer)

    def __repr__(self):
        return "<RAGEvaluation(id='%s', task_id='%s', method='%s', status='%s')>" % (
            self.id,
            self.task_id,
            self.method,
            self.status
        )


class PromptEvaluation(Base):
    __tablename__ = "prompt_evaluation"
    __table_args__ = (Index("ix_prompt_task_id", "task_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer)
    abstract = Column(String(16))
    method = Column(String(32))
    input_id = Column(Integer)
    input_text = Column(String)
    output_id = Column(Integer)
    output_text = Column(String)
    autofill = Column(String)  # 是否允许系统自动填充 auto, manual, none
    status = Column(String(16))  # waiting, evaluating, success, failed
    created = Column(Integer)
    started = Column(Integer)
    finished = Column(Integer)

    def __repr__(self):
        return "<PromptEvaluation(id='%s', task_id='%s', method='%s',autofill:'%s', status='%s')>" % (
            self.id,
            self.task_id,
            self.method,
            self.autofill,
            self.status
        )


class InputFile(Base):
    __tablename__ = "input_file"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    file_name = Column(String(32))
    size: int = Column(Integer)


class OutputFile(Base):
    __tablename__ = "output_file"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    file_name = Column(String(32))
    size: int = Column(Integer)


class TaskPlot(Base):
    __tablename__ = "task_plot"
    __table_args__ = (Index("ix_plot_task_id", "task_id"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer)
    method = Column(String(32))
    link = Column(String)
