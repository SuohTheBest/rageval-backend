import os
from queue import Full

from models.Task import *
from typing import List
from database import SessionLocal
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
        upload_file = UploadFile(
            user_id=user_id, file_name=file_name, size=size)
        db.add(upload_file)
        db.commit()
        return upload_file.id
    finally:
        db.close()


async def get_new_output_id(user_id: int, file_name: str, size: int) -> int:
    db = SessionLocal()
    try:
        download_file = UploadFile(
            user_id=user_id, file_name=file_name, size=size)
        db.add(download_file)
        db.commit()
        return download_file.id
    finally:
        db.close()


async def add_tasks(name: str, method: str, category: str, file_ids: List[int], user_id: int):
    db = SessionLocal()
    for file_id in file_ids:
        upload_file = db.get(UploadFile, file_id)
        if upload_file is None or upload_file.user_id != user_id:
            continue
        new_task = Task(user_id=user_id, name=name, method=method, category=category, input_id=file_id,
                        status="waiting", created=int(time.time()))
        try:
            worker.add_task(new_task.id)
        except Full:
            pass
        db.add(new_task)
    db.commit()
    db.close()


async def get_task_from_id(task_id: int) -> Task:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        return task
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


async def get_tasks_from_user_id(user_id: int, category: str, is_finished: bool) -> List[Task]:
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(
            Task.user_id == user_id).filter(Task.category == category)
        if is_finished:
            tasks = tasks.filter((Task.status == "success") | (
                Task.status == "failed"))  # 不是python or!!!
        else:
            tasks = tasks.filter((Task.status == "waiting")
                                 | (Task.status == "evaluating"))
        tasks = tasks.order_by(Task.created.desc()).all()
        return tasks
    finally:
        db.close()


async def remove_task(task_id: int, user_id: int):
    db = SessionLocal()
    task = db.get(Task, task_id)
    if task is None or task.user_id != user_id:
        return
    try:
        if task.input_id:
            upload_file_path = get_upload_filepath(task.input_id)
            upload_file = db.get(UploadFile, task.input_id)
            if upload_file:
                db.delete(upload_file)
                os.remove(upload_file_path)
        if task.output_id:
            download_file_path = get_download_filepath(task.output_id)
            download_file = db.get(DownloadFile, task.output_id)
            if download_file:
                db.delete(download_file)
                os.remove(download_file_path)
    except Exception as e:
        pass
    finally:
        db.delete(task)
        db.commit()
        db.close()


async def get_fileinfo(user_id: int, category: str, id: int):
    db = SessionLocal()
    try:
        file = None
        if category == "input":
            file = db.get(UploadFile, id)
        elif category == "output":
            file = db.get(DownloadFile, id)
        if file is None or file.user_id != user_id:
            return None
        return file
    finally:
        db.close()
