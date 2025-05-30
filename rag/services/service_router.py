from fastapi import APIRouter

from rag.services.terraria_search import search_router

router = APIRouter(prefix="/service", tags=["services"])

router.include_router(search_router.router)
