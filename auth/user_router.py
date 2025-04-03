from fastapi import APIRouter, Response
from pydantic import BaseModel

import access_token
from auth import utils

router = APIRouter(prefix='/user', tags=['Users'])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    confirm: str


@router.post("/register")
async def register(r: RegisterRequest):
    try:
        await utils.add_user(r.username, r.email, r.password)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


class LoginRequest(BaseModel):
    account: str
    password: str


@router.post("/login")
async def login(r: LoginRequest, response: Response):
    try:
        usr = await utils.get_user_by_username(r.account, r.password)
        if usr is None:
            usr = await utils.get_user_by_email(r.account, r.password)
        if usr is None:
            return {"success": False, "message": "User not found."}
        jwt_str = access_token.create_access_token(str(usr.id))
        response.set_cookie(
            key="access_token",
            value=jwt_str,
            httponly=True,
            max_age=access_token.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=True,
            samesite="lax"
        )
        return {"success": True, "name": usr.username, "avatar": usr.avatar}
    except Exception as e:
        return {"success": False, "message": str(e)}
