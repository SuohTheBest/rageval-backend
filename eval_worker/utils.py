import os
import time

from models.Task import *
from typing import List
from database import db
from eval_worker.worker import waiting_list

UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_upload_filepath(input_id: int):
    file_path = os.path.join(UPLOAD_DIR, str(input_id) + '.csv')
    return file_path


def get_download_filepath(output_id: int):
    file_path = os.path.join(DOWNLOAD_DIR, str(output_id) + '.csv')
    return file_path


async def get_new_input_id(user_id: int):
    upload_file = UploadFile(user_id=user_id)
    db.add(upload_file)
    db.commit()
    return upload_file.id


async def add_tasks(name: str, method: str, file_ids: List[int], user_id: int):
    for file_id in file_ids:
        upload_file = db.get(UploadFile, file_id)
        if upload_file is None or upload_file.user_id != user_id:
            continue
        new_task = Task(user_id=user_id, name=name, method=method, input_id=file_id, status="waiting",
                        created=int(time.time()))
        if waiting_list.not_full:
            waiting_list.put(new_task)
        db.add(new_task)
    db.commit()


async def get_task_from_id(task_id: int) -> Task:
    task = db.get(Task, task_id)
    return task


async def get_tasks_from_user_id(user_id: int) -> List[Task]:
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    return tasks


async def remove_task(task_id: int, user_id: int):
    task = db.get(Task, task_id)
    if task is None or task.user_id != user_id:
        return
    upload_file_path = get_upload_filepath(task.input_id)
    upload_file = db.get(UploadFile, task.input_id)
    if upload_file:
        db.delete(upload_file)
    os.remove(upload_file_path)
    if task.status == "success":
        download_file_path = get_download_filepath(task.output_id)
        download_file = db.get(DownloadFile, task.output_id)
        if download_file:
            db.delete(download_file)
        os.remove(download_file_path)
    elif task.status == "evaluating":
        # TODO
        ...
    db.delete(task)
