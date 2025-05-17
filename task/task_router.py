from fastapi import APIRouter, UploadFile, File, HTTPException, Cookie
from fastapi.responses import FileResponse
from typing import Literal
from fastapi import Query

from prompt.metrics import prompt_metric_list
from prompt.plot import get_prompt_plot
from rag_eval.plot import get_rag_plot
from access_token import get_user_id
from task.request_model import *
from task.utils import *
from rag_eval.rag_eval import rag_metric_list
from models.Task import CustomMetric
from models.database import SessionLocal

router = APIRouter(prefix='/task', tags=['Tasks'])


@router.get("/metrics")
async def get_metrics(category: Literal["rag", "prompt"] = Query(...), access_token: str = Cookie(None)):
    """获取所有可用指标"""
    try:
        user_id = await get_user_id(access_token)
        if category == "prompt":
            # 暂时只有prompt支持自定义
            custom_metrics = await get_custom_metrics(user_id, category)
        else:
            custom_metrics = []
        if category == "rag":
            system_metrics = rag_metric_list()
        else:
            system_metrics = prompt_metric_list()
        system_metrics = [{"name": m['name'], "type": "system", "description": m['description'], "created": None}
                          for m in system_metrics]
        custom_metrics = [{"name": m.name, "type": "custom", "description": m.description, "created": m.created}
                          for m in custom_metrics]
        return system_metrics + custom_metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def addEvals(r: AddTaskRequest, access_token: str = Cookie(None)):
    """增加任务"""
    try:
        user_id = await get_user_id(access_token)
        await add_evals(r, user_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload(file: UploadFile = File, access_token: str = Cookie(None)):
    """上传文件"""
    try:
        user_id = await get_user_id(access_token)
        content = await file.read()
        length = len(content)
        input_id = await get_new_input_id(user_id, file.filename, length)
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
async def download(category: Literal["input", "output"], file_id: int, access_token: str = Cookie(None)):
    """下载文件"""
    try:
        user_id = await get_user_id(access_token)
        if category == 'input':
            file_path = get_upload_filepath(file_id)
            file_info = await get_fileinfo(user_id, 'input', [file_id])
        else:
            file_path = get_download_filepath(file_id)
            file_info = await get_fileinfo(user_id, 'output', [file_id])
        if file_info is None or file_info[0].user_id != user_id:
            return {"success": False, "message": "No such file."}
        return FileResponse(
            file_path,
            filename=file_info[0].file_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_task(r: DeleteTaskRequest, access_token: str = Cookie(None)):
    """删除任务"""
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
    """获取统计图表"""
    try:
        user_id = await get_user_id(access_token)
        task = await get_task_from_id(task_id, user_id)
        if task is None:
            return {"success": False, "message": "No such task."}
        link = None
        if task.category == "prompt":
            link = get_prompt_plot(task_id, method)
        elif task.category == "rag":
            print("here")
            link = get_rag_plot(task_id, method)
        else:
            pass
        return {"success": True, "url": link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_tasks(category: Literal["rag", "prompt"],
                    access_token: str = Cookie(None)):
    """获取当前用户全部任务"""
    try:
        user_id = await get_user_id(access_token)
        tasks = await get_tasks_from_user_id(user_id, category)
        return {"success": True, "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization")
async def getOptimizations(task_id: int = Query(...), access_token: str = Cookie(None)):
    """获取当前用户全部单轮优化结果"""
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
    """获取当前用户的全部单轮评估"""
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
    """获取文件信息"""
    try:
        user_id = await get_user_id(access_token)
        file_info = await get_fileinfo(user_id, r.category, r.file_ids)
        if file_info:
            return {"success": True, "info": file_info}
        else:
            return {"success": False, "message": "No such file."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metric")
async def add_metric(r: AddMetricRequest, access_token: str = Cookie(None)):
    """添加自定义指标"""
    try:
        user_id = await get_user_id(access_token)
        success = await add_custom_metric(user_id, r.name, r.category, r.description)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add metric.")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/metric")
async def update_metric(r: UpdateMetricRequest, access_token: str = Cookie(None)):
    """更新自定义指标"""
    try:
        user_id = await get_user_id(access_token)
        success = await update_custom_metric(user_id, r.id, r.name, r.description)
        if not success:
            raise HTTPException(status_code=404, detail="Metric not found.")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/metric/{metric_id}")
async def delete_metric(metric_id: int, access_token: str = Cookie(None)):
    """删除自定义指标"""
    try:
        user_id = await get_user_id(access_token)
        success = await delete_custom_metric(user_id, metric_id)
        if not success:
            raise HTTPException(status_code=404, detail="Metric not found")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
