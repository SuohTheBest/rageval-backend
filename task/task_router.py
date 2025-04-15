from typing import List, Literal

from fastapi import APIRouter, UploadFile, File, HTTPException, Cookie, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from task import utils
from access_token import get_user_id
from task.utils import add_tasks, get_upload_filepath, get_task_from_id, get_download_filepath, remove_task, \
    get_tasks_from_user_id

router = APIRouter(prefix='/task', tags=['Tasks'])


class AddTaskRequest(BaseModel):
    name: str
    method: str
    category: str
    input_ids: List[int]


@router.post("/add")
async def addTasks(r: AddTaskRequest, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        await add_tasks(r.name, r.method, r.category, r.input_ids, user_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload(file: UploadFile = File, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        input_id = await utils.get_new_input_id(user_id)
        fpath = get_upload_filepath(input_id)
        with open(fpath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        return {
            "success": True,
            "upload_id": input_id,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()


class DownloadTaskRequest(BaseModel):
    task_id: int
    choose: Literal["upload", "download"]


@router.post("/download")
async def download(r: DownloadTaskRequest, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        task = await get_task_from_id(r.task_id)
        if task is None or task.user_id != user_id:
            return {"success": False, "message": "No such task."}
        if r.choose == 'upload':
            if task.input_id is None:
                return {"success": False, "message": "No such file."}
            file_path = get_upload_filepath(task.input_id)
        else:
            if task.output_id is None:
                return {"success": False, "message": "No such file."}
            file_path = get_download_filepath(task.output_id)
        return FileResponse(
            file_path,
            media_type="text/plain",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/")
async def delete_task(task_id: int = Query(...), access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        await remove_task(task_id, user_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_tasks(category: Literal["rag", "prompt"],
                    is_finished: bool = Query(...),
                    access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        tasks = await get_tasks_from_user_id(user_id, category, is_finished)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
