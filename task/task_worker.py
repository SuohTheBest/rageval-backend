import signal
import sys
import time
from queue import Queue, Full
from multiprocessing import Event
from threading import Thread
from sqlalchemy import Engine
from models.Task import RAGEvaluation, PromptEvaluation
from sqlalchemy.orm import sessionmaker
from models.database import engine
from logger import logger
from prompt.evaluate import process_prompt_task
from task.ragas_metrics import process_rag


class TaskWorkerLauncher:
    def __init__(self):
        self.q = Queue()
        self.event = Event()
        self.worker = TaskWorker(self.q, self.event, engine)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.worker.start()

    def add_eval(self, eval_id: int, task_id: int, category: str):
        try:
            self.q.put_nowait(
                {"id": eval_id, "task_id": task_id, "category": category})
        except Full:
            logger.error("Task queue full! {}".format(eval_id))

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

    def get_eval(self, db):
        if self.queue.empty():
            evals = []
            try:
                rag_evals = db.query(RAGEvaluation).filter(
                    (RAGEvaluation.status == "waiting") | (RAGEvaluation.status == "evaluating")).all()
                prompt_evals = db.query(PromptEvaluation).filter(
                    (PromptEvaluation.status == "waiting") | (PromptEvaluation.status == "evaluating")).all()
                for eval in rag_evals:
                    evals.append({'id': eval.id, 'category': 'rag'})
                for eval in prompt_evals:
                    evals.append({'id': eval.id, 'category': 'prompt'})
            except Exception as e:
                self.logger.error(e)
            for eval in evals:
                try:
                    self.queue.put_nowait(eval)
                except Full:
                    break
        return self.queue.get()

    async def process_eval(self, eval: RAGEvaluation | PromptEvaluation, eval_info):
        category = eval_info['category']
        # task_id = eval_info['task_id']
        try:
            self.logger.info("Processing task: {}".format(eval))
            if category == 'prompt':
                result = process_prompt_task(eval)
                return {"success": True, "result": result}
            else:
                # TODO
                result = await process_rag(eval)
                return {"success": True, "result": result}
        except Exception as e:
            self.logger.error("Processing task failed: {}".format(e))
            return {"success": False}

    async def run(self):
        self.logger.info("Started Task Worker")

        while not self.stop_event.is_set():

            db = self.session()
            try:
                print("try here")
                eval_info = self.get_eval(db)
                if eval_info['category'] == 'prompt':
                    eval_in_db = db.get(PromptEvaluation, eval_info['id'])
                else:
                    eval_in_db = db.get(RAGEvaluation, eval_info['id'])
                if eval_in_db is None or (eval_in_db.status != "waiting" and eval_in_db.status != "evaluating"):
                    continue
                eval_in_db.status = "evaluating"
                eval_in_db.started = int(time.time())
                db.commit()
                # start work
                print("start work")
                result = await self.process_eval(eval_in_db, eval_info)
                # finish work
                if eval_info['category'] == 'prompt':
                    eval_in_db = db.get(PromptEvaluation, eval_info['id'])
                else:
                    eval_in_db = db.get(RAGEvaluation, eval_info['id'])
                if eval_in_db is None:
                    print("none is here")
                    continue
                print("here is success:")
                print(result)
                print(result["success"])

                eval_in_db.status = "success" if result["success"] else "failed"
                print(eval_in_db.status)
                eval_in_db.finished = int(time.time())
                # set other properties
                # TODO
                if "result" in result:
                    eval_in_db.output_text = str(result["result"])
                # exception
                db.commit()
            except Exception as e:
                print(f"Exception occurred: {e}")
                db.rollback()
            finally:
                db.close()
        self.engine.dispose()
