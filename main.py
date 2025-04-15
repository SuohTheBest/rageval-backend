from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from fastapi import FastAPI
from auth import user_router
from task import task_router

g_prefix = '/api'

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(user_router.router, prefix=g_prefix)
app.include_router(task_router.router, prefix=g_prefix)


@app.get("/")
async def root():
    return {"message": "Hello World!"}

