import os

from fastapi import APIRouter, UploadFile, File, HTTPException, Cookie
from pydantic import BaseModel
from eval_worker import utils
from access_token import get_user_id

router = APIRouter(prefix='/task', tags=['Tasks'])
UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class AddTaskRequest(BaseModel):
    name: str
    input_id: int
    method: str


@router.post("/add")
async def add(r: AddTaskRequest):
    ...


@router.post("/upload")
async def upload(file: UploadFile = File, access_token: str = Cookie(None)):
    try:
        user_id = await get_user_id(access_token)
        upload_id = await utils.get_upload_id(user_id)
        file_path = os.path.join(UPLOAD_DIR, str(upload_id) + '.csv')
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        return {
            "success": True,
            "upload_id": upload_id,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()

