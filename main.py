import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from rag import rag_router
from models.database import Base, engine
from models import Task, Text, User
from fastapi import FastAPI
from auth import user_router
from task import task_router

g_prefix = "/api"

Base.metadata.create_all(bind=engine)

origins = [
    "http://47.97.175.75",
    "https://47.97.175.75",
    "http://localhost",
    "https://localhost",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)

app.mount("/static", StaticFiles(directory="./eval_plots"))
app.include_router(user_router.router, prefix=g_prefix)
app.include_router(task_router.router, prefix=g_prefix)
app.include_router(rag_router.router, prefix=g_prefix)


@app.get("/")
async def root():
    return {"message": "Hello World!"}
