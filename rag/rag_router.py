from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix='/chat', tags=['RagChat'])


class FeatureOperation(BaseModel):
    name: str
    icon: str | None = None
    require: str = "none"  # none, picture, file


class RAGInstance(BaseModel):
    id: str
    name: str
    description: str
    icon: str | None = None
    operations: List[FeatureOperation]


@router.get("/assistants")
async def get_assistants():
    # 获取所有可用的RAG助手列表
    assistants = [
        RAGInstance(
            id="terraria",
            name="🗡️🌳✨泰拉瑞亚助手🗡️🌳✨",
            description="专门解答泰拉瑞亚游戏相关问题的AI助手，包括武器数据、敌怪机制、Boss攻略等",
            icon="assistants/terraria.png",
            operations=[
                FeatureOperation(
                    name="游戏截图上传",
                    icon="operations/picture.svg",
                    require="picture"
                ),
                FeatureOperation(
                    name="游戏存档分析",
                    icon="operations/savefile.png",
                    require="file"
                ),
            ]
        ),
        RAGInstance(
            id="op",
            name="原神助手",
            description="启动一下",
            icon="assistants/op.png",
            operations=[]
        )
    ]

    return {"assistants": assistants}
