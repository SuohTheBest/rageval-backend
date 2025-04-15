import os
import time

from fastapi import HTTPException
from jose import jwt, JWTError
from database import SessionLocal

from models.User import User

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if JWT_SECRET_KEY is None:
    JWT_SECRET_KEY = "dummy-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 5


def create_access_token(subject: str, expires_minutes: int = None) -> str:
    if expires_minutes is not None:
        expires_minutes = int(time.time()) + expires_minutes * 60
    else:
        expires_minutes = int(time.time()) + ACCESS_TOKEN_EXPIRE_MINUTES * 60

    to_encode = {"exp": expires_minutes, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt


async def get_user_id(token: str) -> int:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Not logged in.",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        usr_id: str = payload.get("sub")
        expires: int = payload.get("exp")
        if usr_id is None or expires is None:
            raise credentials_exception
        if time.time() > expires:
            raise HTTPException(
                status_code=401,
                detail="Old token.",
            )
    except JWTError:
        raise credentials_exception
    return int(usr_id)


async def get_current_user(token: str) -> User:
    user_id = await get_user_id(token)
    db = SessionLocal()
    user = db.get(User, user_id)
    db.close()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )
    return user
