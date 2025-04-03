import os
import time

from fastapi import HTTPException
from jose import jwt, JWTError
from database import db

from auth.user_models import User

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


def get_current_user(token: str):
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
    user = db.get(User, int(usr_id))
    if user is None:
        raise credentials_exception
    return user
