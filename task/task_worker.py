import logging
import signal
import sys
import time
from queue import Queue, Full
from multiprocessing import Event
from threading import Thread
from time import sleep

from sqlalchemy import Engine
import os
from models.Task import Task
from sqlalchemy.orm import sessionmaker
from logging import getLogger
from database import engine
from logger import logger
# rag
import pandas as pd
import os
from ragas import SingleTurnSample, EvaluationDataset
from ragas.metrics import BleuScore
from ragas.llms import LangchainLLMWrapper
# 原本的导入
# from task.utils import get_upload_filepath, get_task_from_id, get_download_filepath, remove_task
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from ragas.metrics import LLMContextRecall, Faithfulness, FactualCorrectness
from ragas import evaluate
from models.Task import Task
from task.metrics import *
from sqlalchemy.exc import SQLAlchemyError
import ast


class TaskWorkerLauncher:
    def __init__(self):
        self.q = Queue()
        self.event = Event()
        self.worker = TaskWorker(self.q, self.event, engine)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.worker.start()

    def add_task(self, task_id: int):
        self.q.put(task_id)

    def signal_handler(self, sig, frame):
        self.event.set()
        sys.exit(0)


def process_rag(task: Task):
    os.environ["OPENAI_API_KEY"] = "sk-JUbjcL4UL7rCP6mrU2qGQKTE8Um0KJwAnWGE5lDebQc1iO71"
    os.environ["OPENAI_API_BASE"] = "https://api.chatanywhere.tech/v1"
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    evaluator_llm = LangchainLLMWrapper(llm)
    from task.utils import get_upload_filepath
    # 这里回头当做做表用的ids，到时候需要解包
    input_ids = []
    input_ids.append(task.input_id)
    # 这里要处理的肯定是最后一个文件
    file = get_upload_filepath(input_ids[-1])
    user_input = []
    response = []
    reference = []
    retrieved_contexts = [[]]
    reference_contexts = [[]]
    df = pd.read_csv(file)
    user_input = df.get('user_input', pd.Series([])
                        ).tolist()  # 如果 'a' 不存在，返回空列表
    response = df.get('response', pd.Series([])).tolist()  # 如果 'a' 不存在，返回空列表
    reference = df.get('reference', pd.Series([])).tolist()  # 如果 'a' 不存在，返回空列表
    # retrieved_contexts = df.get('retrieved_contexts', pd.Series([[]])).tolist()
    # reference_contexts = df.get('reference_contexts', pd.Series([[]])).tolist()
    retrieved_contexts = [ast.literal_eval(item) if isinstance(
        item, str) else item for item in df.get('retrieved_contexts', pd.Series([[]])).tolist()]
    reference_contexts = [ast.literal_eval(item) if isinstance(
        item, str) else item for item in df.get('reference_contexts', pd.Series([[]])).tolist()]
    methods = []
    print("here1")
    methods.append(task.method)
    for method in methods:
        if method == "method1":
            print("here")
            process_LLMContextPrecisionWithoutReference(
                user_input, response, retrieved_contexts, df)
    df.to_csv(f'{task.id}_output.csv', index=False)


class TaskWorker(Thread):
    def __init__(self, queue: Queue, stop_event: Event, sqlengine: Engine):
        Thread.__init__(self, daemon=True)
        self.engine = sqlengine
        self.logger = logger
        self.session = sessionmaker(autocommit=False, bind=self.engine)
        self.queue = queue
        self.stop_event = stop_event

    def get_task(self, db):
        if self.queue.empty():
            try:
                tasks = db.query(Task).filter(Task.status == 'waiting').all()
            except SQLAlchemyError as e:
                print(f"SQLAlchemyError: {e}")
            except Exception as e:
                print(f"Exception: {e}")
            for task in tasks:
                try:
                    self.queue.put_nowait(task.id)
                except Full:
                    break
        return self.queue.get()

    def process_task(self, task):
        try:
            self.logger.info("Processing task: {}".format(task))
            # TODO
            print("process")
            process_rag(task)
            # sleep(600)
            return {'success': True}
        except Exception as e:
            self.logger.error("Processing task failed: {}".format(e))
            return {'success': False}

    def run(self):
        self.logger.info("Started Task Worker")
        print(self.stop_event.is_set())
        while not self.stop_event.is_set():
            db = self.session()
            try:
                task_id: int = self.get_task(db)
                task_in_db = db.get(Task, task_id)
                # print(task_in_db)
                if task_in_db is None or task_in_db.status != 'waiting':
                    continue
                task_in_db.status = 'evaluating'
                task_in_db.started = int(time.time())
                db.commit()
                # start work
                print("start")
                result = self.process_task(task_in_db)
                print("end")
                # finish work
                task_in_db = db.get(Task, task_id)
                if task_in_db is None:
                    continue
                task_in_db.status = 'success' if result['success'] else 'failed'
                task_in_db.finished = int(time.time())
                # set other properties
                # TODO
                db.commit()
            except Exception as e:
                # print("Exception")
                db.rollback()
            finally:
                db.close()
        self.engine.dispose()
