import logging
import signal
import sys
import time
from queue import Queue, Full
from multiprocessing import Event
from threading import Thread
from time import sleep

from sqlalchemy import Engine

from models.Task import Task
from sqlalchemy.orm import sessionmaker
from logging import getLogger
from database import engine
from logger import logger

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
            tasks = db.query(Task).filter(Task.status == 'waiting').all()
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
            sleep(600)
            return {'success': True}
        except Exception as e:
            self.logger.error("Processing task failed: {}".format(e))
            return {'success': False}

    def run(self):
        self.logger.info("Started Task Worker")
        while not self.stop_event.is_set():
            db = self.session()
            try:
                task_id: int = self.get_task(db)
                task_in_db = db.get(Task, task_id)
                if task_in_db is None or task_in_db.status != 'waiting':
                    continue
                task_in_db.status = 'evaluating'
                task_in_db.started = int(time.time())
                db.commit()
                # start work
                result = self.process_task(task_in_db)
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
                db.rollback()
            finally:
                db.close()
        self.engine.dispose()
