from fastapi import APIRouter, UploadFile, File, HTTPException, Cookie
from fastapi.responses import FileResponse

from prompt.metrics import metric_list
from prompt.plot import get_prompt_plot
from task import utils
from access_token import get_user_id
from task.request_model import *
from task.utils import *
from task.ragas_metrics import rag_list

router = APIRouter(prefix='/task', tags=['Tasks'])


@router.get("/methods")
async def get_methods(category: Literal["rag", "prompt"] = Query(...)):
    # TODO
    if category == "rag":
        return rag_list()
    else:
        return metric_list()


@router.post("/")
async def addEvals(r: AddTaskRequest, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        await add_evals(r, user_id)
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
        task = await get_task_from_id(task_id, user_id)
        if task is None or task.user_id != user_id:
            return {"success": False, "message": "No such task."}
        curr_eval = await get_eval_from_id(eval_id, task.category)
        if category == 'input':
            if curr_eval.input_id is None:
                return {"success": False, "message": "No such file."}
            file_path = get_upload_filepath(curr_eval.input_id)
            file_info = await get_fileinfo(user_id, 'input', [curr_eval.input_id])
        else:
            if curr_eval.output_id is None:
                return {"success": False, "message": "No such file."}
            file_path = get_download_filepath(curr_eval.output_id)
            file_info = await get_fileinfo(user_id, 'output', [curr_eval.output_id])
        if file_info is None:
            return {"success": False, "message": "No such file."}
        return FileResponse(
            file_path,
            filename=file_info[0].file_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_task(r: DeleteTaskRequest, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        if r.eval_ids is None or len(r.eval_ids) <= 0:
            await remove_task(r.task_id, user_id)
        else:
            task = await get_task_from_id(r.task_id, user_id)
            if task is None:
                return {"success": False, "message": "No such task."}
            await remove_eval(r.eval_ids, category=task.category)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plot")
async def getPlot(task_id: int = Query(...), method: str = Query(...), access_token: str = Cookie(None)):
    db = SessionLocal()
    try:
        user_id = await get_user_id(access_token)
        task = await get_task_from_id(task_id, user_id)
        if task is None:
            return {"success": False, "message": "No such task."}
        link = await get_plot(task_id, method)
        if link is None:
            # TODO 应该在这里生成图表
            link = None
            if task.category == "prompt":
                link = get_prompt_plot(task_id, method)
                curr_prompt_plot = TaskPlot(task_id=task_id,method=method,link=link)
                db.add(curr_prompt_plot)

            else:
                pass

        db.commit()
        return {"success": True, "url": link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/")
async def get_tasks(category: Literal["rag", "prompt"],
                    access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        tasks = await get_tasks_from_user_id(user_id, category)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization")
async def getOptimizations(task_id: int = Query(...), access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        task = await get_task_from_id(task_id, user_id)
        if task is None or task.category != 'prompt':
            return {"success": False, "message": "No such task."}
        optimizations = await get_optimizations(task_id)
        return {"success": True, "optimizations": optimizations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allevals")
async def get_evals(task_id: int = Query(...), access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        task = await get_task_from_id(task_id, user_id)
        if task is None:
            return {"success": False, "message": "No such task."}
        evals = await get_evals_from_task_id(task_id, category=task.category)
        plots = await get_plots(task.id)
        return {"success": True, "evals": evals, "plots": plots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fileinfo")
async def getFileinfo(r: GetFileInfoRequest, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        file_info = await get_fileinfo(user_id, r.category, r.file_ids)
        if file_info:
            return {"success": True, "info": file_info}
        else:
            return {"success": False, "message": "No such file."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
