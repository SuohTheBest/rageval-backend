import time
from queue import Queue
from multiprocessing import Process, Event
from time import sleep

from models.Task import Task

has_overflow = True

MAX_QUEUE_SIZE = 100
waiting_list = Queue(maxsize=MAX_QUEUE_SIZE)


class TaskWorker(Process):
    def __init__(self, queue: Queue, stop_event: Event):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        Process.__init__(self, daemon=True)
        self.queue = queue
        self.stop_event = stop_event
        self.engine = create_engine("sqlite:///../database.db", connect_args={"check_same_thread": False},
                                    echo=False)
        self.session = sessionmaker(autocommit=False, bind=self.engine)

    def get_task(self, db):
        global has_overflow
        if self.queue.empty() and has_overflow:
            tasks = db.query(Task).filter(Task.status == 'waiting').limit(MAX_QUEUE_SIZE).all()
            if len(tasks) >= MAX_QUEUE_SIZE:
                has_overflow = True
            else:
                has_overflow = False
            for task in tasks:
                self.queue.put(task, timeout=5)
        return self.queue.get()

    def process_task(self, task):
        try:
            # TODO
            sleep(10)
            return 'success'
        except Exception as e:
            return 'fail'

    def run(self):
        while not self.stop_event.is_set():
            db = self.session()
            try:
                task: Task = self.get_task(db)
                task_in_db = db.get(Task, task.id)
                if task_in_db is None:
                    continue
                task_in_db.status = 'evaluating'
                task_in_db.started = int(time.time())
                db.commit()
                # start work
                status = self.process_task(task)
                # finish work
                task_in_db = db.get(Task, task.id)
                if task_in_db is None:
                    continue
                task_in_db.status = status
                task_in_db.finished = int(time.time())
                # set other properties
                # TODO
                db.commit()
            except Exception as e:
                db.rollback()
            finally:
                db.close()
        self.engine.dispose()
