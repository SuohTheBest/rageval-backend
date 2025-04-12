from models import Task
from database import db


async def get_upload_id(user_id: int):
    upload_file = Task.UploadFile(user_id=user_id)
    db.add(upload_file)
    db.commit()
    return upload_file.id

