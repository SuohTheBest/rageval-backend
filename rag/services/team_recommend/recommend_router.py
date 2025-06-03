from fastapi import APIRouter
from os import path

router = APIRouter(prefix="/gok", tags=["GOK"])


async def get_team_recommend_double(hero_name: str) -> str | None:
    file_path = f"./static/recommend/{hero_name}_双排.jpg"
    if not path.exists(file_path):
        return None
    return f"recommend/{hero_name}_双排.jpg"


async def get_team_recommend_triple(hero_name: str) -> str | None:
    file_path = f"./static/recommend/{hero_name}_三排.jpg"
    if not path.exists(file_path):
        return None
    return f"recommend/{hero_name}_三排.jpg"


@router.get("/recommendations")
async def get_team_recommendations(hero_name: str):
    double_url = await get_team_recommend_double(hero_name)
    triple_url = await get_team_recommend_triple(hero_name)
    return {
        "success": True,
        "data": {
            "double_url": double_url,
            "triple_url": triple_url
        }
    }
