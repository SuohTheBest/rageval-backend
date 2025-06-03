from fastapi import APIRouter

from rag.services.team_recommend import recommend_router
from rag.services.terraria_search import search_router

router = APIRouter(prefix="/service", tags=["services"])

router.include_router(search_router.router)
router.include_router(recommend_router.router)
