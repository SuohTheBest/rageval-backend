from fastapi import APIRouter, UploadFile, File, HTTPException, Cookie, Query
from fastapi.responses import FileResponse

from task import utils
from access_token import get_user_id
from task.request_model import *
from task.utils import *

router = APIRouter(prefix='/task', tags=['Tasks'])


@router.post("/")
async def addTasks(r: AddTaskRequest, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        await add_tasks(r, user_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload(file: UploadFile = File, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        content = await file.read()
        length = len(content)
        input_id = await utils.get_new_input_id(user_id, file.filename, length)
        fpath = get_upload_filepath(input_id)
        with open(fpath, "wb") as buffer:
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


@router.get("/download")
async def download(category: Literal["input", "output"], task_id: int, eval_id: int, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        task = await get_task_from_id(task_id)
        if task is None or task.user_id != user_id:
            return {"success": False, "message": "No such task."}
        curr_eval = await get_eval_from_id(eval_id)
        if category == 'input':
            if curr_eval.input_id is None:
                return {"success": False, "message": "No such file."}
            file_path = get_upload_filepath(curr_eval.input_id)
            file_info = await get_fileinfo(user_id, 'input', curr_eval.input_id)
        else:
            if curr_eval.output_id is None:
                return {"success": False, "message": "No such file."}
            file_path = get_download_filepath(curr_eval.output_id)
            file_info = await get_fileinfo(user_id, 'output', curr_eval.output_id)
        if file_info is None:
            return {"success": False, "message": "No such file."}
        return FileResponse(
            file_path,
            filename=file_info.file_name
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
                    access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        tasks = await get_tasks_from_user_id(user_id, category)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fileinfo")
async def getFileinfo(category: Literal["input", "output"], file_id: int, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        file_info = await get_fileinfo(user_id, category, file_id)
        if file_info:
            return {"success": True, "id": file_info.id, "name": file_info.file_name, "size": file_info.size}
        else:
            return {"success": False, "message": "No such file."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alter")
async def alterTask(r: AlterTaskRequest, access_token: str = Cookie(None)):
    try:
        # TODO
        user_id = await get_user_id(access_token)
        await alter_task(user_id, r.task_id, r.name, r.method)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
