import os
from queue import Full
from models.Task import *
from models.database import SessionLocal
from task.request_model import *
from task.task_worker import TaskWorkerLauncher

UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

worker = TaskWorkerLauncher()


def get_upload_filepath(input_id: int):
    file_path = os.path.join(UPLOAD_DIR, str(input_id))
    return file_path


def get_download_filepath(output_id: int):
    file_path = os.path.join(DOWNLOAD_DIR, str(output_id))
    return file_path


async def get_new_input_id(user_id: int, file_name: str, size: int) -> int:
    db = SessionLocal()
    try:
        upload_file = InputFile(user_id=user_id, file_name=file_name, size=size)
        db.add(upload_file)
        db.commit()
        return upload_file.id
    finally:
        db.close()


async def get_new_output_id(user_id: int, file_name: str, size: int) -> int:
    db = SessionLocal()
    try:
        download_file = InputFile(user_id=user_id, file_name=file_name, size=size)
        db.add(download_file)
        db.commit()
        return download_file.id
    finally:
        db.close()


async def add_evals(r: AddTaskRequest, user_id: int):
    db = SessionLocal()
    if r.task_id:
        curr_task = db.get(Task, r.task_id)
        if curr_task is None:
            db.close()
            return
    else:
        curr_task = Task(user_id=user_id, name=r.name, category=r.category)
        db.add(curr_task)
    if r.input_ids:
        for file_id in r.input_ids:
            upload_file = db.get(InputFile, file_id)
            if upload_file is None or upload_file.user_id != user_id:
                continue
            for method in r.methods:
                new_eval = Evaluation(task_id=curr_task.id,
                                      abstract=upload_file.file_name[0:10],
                                      method=method,
                                      input_id=file_id,
                                      status='waiting',
                                      created=int(time.time()))
                try:
                    worker.add_eval(new_eval.id)
                except Full:
                    pass
                db.add(new_eval)
    elif r.input_texts:
        for input_text in r.input_texts:
            for method in r.methods:
                new_eval = Evaluation(task_id=curr_task.id,
                                      abstract=input_text[0:10],
                                      method=method,
                                      input_text=input_text,
                                      status='waiting',
                                      created=int(time.time()))
                try:
                    worker.add_eval(new_eval.id)
                except Full:
                    pass
                db.add(new_eval)
    db.commit()
    db.close()


async def get_task_from_id(task_id: int, user_id: int) -> Task | None:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None or task.user_id != user_id:
            return None
        return task
    finally:
        db.close()


async def get_eval_from_id(eval_id: int) -> Evaluation:
    db = SessionLocal()
    try:
        e = db.get(Evaluation, eval_id)
        return e
    finally:
        db.close()


async def alter_task(user_id: int, task_id: int, name: str, method: str):
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None or task.user_id != user_id:
            return None
        task.name = name
        task.method = method
        db.commit()
    finally:
        db.close()


async def get_tasks_from_user_id(user_id: int, category: str) -> List[Task]:
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.user_id == user_id).filter(Task.category == category).all()
        return tasks
    finally:
        db.close()


async def get_evals_from_task_id(task_id: int) -> List[Evaluation]:
    db = SessionLocal()
    try:
        evals = db.query(Evaluation).filter(Evaluation.task_id == task_id).all()
        return evals
    finally:
        db.close()


async def remove_task(task_id: int, user_id: int):
    db = SessionLocal()
    task = await get_task_from_id(task_id, user_id)
    if task is None:
        return
    assigned_evals = await get_evals_from_task_id(task_id)
    for e in assigned_evals:
        try:
            if e.input_id:
                upload_file_path = get_upload_filepath(e.input_id)
                upload_file = db.get(InputFile, e.input_id)
                if upload_file:
                    db.delete(upload_file)
                    os.remove(upload_file_path)
            if e.output_id:
                download_file_path = get_download_filepath(e.output_id)
                download_file = db.get(OutputFile, e.output_id)
                if download_file:
                    db.delete(download_file)
                    os.remove(download_file_path)
            db.delete(e)
        except Exception:
            pass
    db.delete(task)
    db.commit()
    db.close()


async def remove_eval(eval_ids: List[int]):
    # need check user_id before use
    db = SessionLocal()
    for eval_id in eval_ids:
        try:
            eval = db.get(Evaluation, eval_id)
            if eval is None:
                return
            db.delete(eval)
        except Exception:
            pass
    db.commit()
    db.close()


async def get_fileinfo(user_id: int, category: str, ids: List[int]):
    db = SessionLocal()
    ans = []
    try:
        for id in ids:
            file = None
            if category == "input":
                file = db.get(InputFile, id)
            elif category == "output":
                file = db.get(OutputFile, id)
            if file is None or file.user_id != user_id:
                continue
            ans.append(file)
        return ans
    finally:
        db.close()
