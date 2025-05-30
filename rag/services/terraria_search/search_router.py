from fastapi import APIRouter

from rag.services.terraria_search.search_api import get_crafting_info

router = APIRouter(prefix="/terraria", tags=["terraria_search"])


@router.get("/tree")
async def get_tree(item: str):
    tree = await get_crafting_info(item)
    return tree
