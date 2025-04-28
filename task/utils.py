import os
from queue import Full

from sqlalchemy import insert

from models.Task import *
from models.database import SessionLocal
from task.request_model import *
from task.task_worker import TaskWorkerLauncher

UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs("eval_plots", exist_ok=True)

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
        upload_file = InputFile(
            user_id=user_id, file_name=file_name, size=size)
        db.add(upload_file)
        db.commit()
        return upload_file.id
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
        db.commit()
    input_ids = r.input_ids if r.input_ids else []
    input_texts = r.input_texts if r.input_texts else []
    eval_dict = {"task_id": curr_task.id, "status": 'waiting', "created": int(time.time())}
    if r.category == "prompt":
        eval_dict["autofill"] = r.autofill
        eval_dict["user_fill"] = r.user_fill
    new_evals = []
    for file_id in input_ids:
        upload_file = db.get(InputFile, file_id)
        if upload_file is None or upload_file.user_id != user_id:
            continue
        for method in r.methods:
            curr_eval = eval_dict.copy()
            curr_eval["abstract"] = upload_file.file_name[0:10]
            curr_eval["method"] = method
            curr_eval["input_id"] = file_id
            if method != "自定义" or not r.custom_methods or len(r.custom_methods) <= 0:
                new_evals.append(curr_eval)
            else:
                for custom_method in r.custom_methods:
                    if len(custom_method) <= 0:
                        continue
                    temp = curr_eval.copy()
                    temp["method"] = custom_method
                    new_evals.append(temp)

    for input_text in input_texts:
        if input_text is None:
            continue
        for method in r.methods:
            curr_eval = eval_dict.copy()
            curr_eval["abstract"] = input_text[0:10]
            curr_eval["method"] = method
            curr_eval["input_text"] = input_text
            if method != "自定义" or not r.custom_methods or len(r.custom_methods) <= 0:
                new_evals.append(curr_eval)
            else:
                for custom_method in r.custom_methods:
                    if len(custom_method) <= 0:
                        continue
                    temp = curr_eval.copy()
                    temp["method"] = custom_method
                    new_evals.append(temp)

    last_input = new_evals[0]["input_id"] if ("input_id" in new_evals[0]) else new_evals[0]["input_text"]
    for eval in new_evals:
        if r.category == "prompt":
            eval_obj = PromptEvaluation(**eval)
        else:
            eval_obj = RAGEvaluation(**eval)
        db.add(eval_obj)
        curr_input = eval["input_id"] if ("input_id" in eval) else eval["input_text"]
        if curr_input != last_input:
            worker.add_eval(-1, curr_task.id, user_id, r.category)  # 当前轮次结束
        db.commit()
        worker.add_eval(eval_obj.id, curr_task.id, user_id, r.category)
    if len(new_evals) > 0:
        worker.add_eval(-1, curr_task.id, user_id, r.category)
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


async def get_eval_from_id(eval_id: int, category: str) -> RAGEvaluation | PromptEvaluation:
    db = SessionLocal()
    try:
        if category == 'prompt':
            e = db.get(PromptEvaluation, eval_id)
        else:
            e = db.get(RAGEvaluation, eval_id)
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
        tasks = db.query(Task).filter(Task.user_id == user_id).filter(
            Task.category == category).all()
        return tasks
    finally:
        db.close()


async def get_evals_from_task_id(task_id: int, category: str) -> List[RAGEvaluation | PromptEvaluation]:
    db = SessionLocal()
    try:
        if category == 'prompt':
            evals = db.query(PromptEvaluation).filter(
                PromptEvaluation.task_id == task_id).all()
        else:
            evals = db.query(RAGEvaluation).filter(
                RAGEvaluation.task_id == task_id).all()
        return evals
    finally:
        db.close()


async def get_plot(task_id: int, method: str):
    db = SessionLocal()
    try:
        plot = db.query(TaskPlot).filter(TaskPlot.task_id == task_id).filter(
            TaskPlot.method == method).first()
        if plot is None:
            return None
        return plot.link
    finally:
        db.close()


async def get_plots(task_id: int):
    db = SessionLocal()
    try:
        plot = db.query(TaskPlot).filter(TaskPlot.task_id == task_id).all()
        if plot is None:
            return []
        return plot
    finally:
        db.close()


async def get_optimizations(task_id: int):
    db = SessionLocal()
    try:
        optimizations = db.query(Optimization).filter(Optimization.task_id == task_id).all()
        if optimizations is None:
            return []
        return optimizations
    finally:
        db.close()


async def remove_task(task_id: int, user_id: int):
    db = SessionLocal()
    task = await get_task_from_id(task_id, user_id)
    if task is None:
        return
    assigned_evals = await get_evals_from_task_id(task_id, task.category)
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
    optimizations = db.query(Optimization).filter(Optimization.task_id == task_id).all()
    if optimizations:
        for e in optimizations:
            db.delete(e)
    db.delete(task)
    db.commit()
    db.close()


async def remove_eval(eval_ids: List[int], category: str):
    # need check user_id before use
    db = SessionLocal()
    task_id = -1
    for eval_id in eval_ids:
        try:
            if category == 'prompt':
                eval = db.get(PromptEvaluation, eval_id)
            else:
                eval = db.get(RAGEvaluation, eval_id)
            if eval is None:
                return
            task_id = eval.task_id
            db.delete(eval)
        except Exception:
            pass
    optimizations = db.query(Optimization).filter(Optimization.task_id == task_id).all()
    if optimizations:
        for e in optimizations:
            db.delete(e)
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
