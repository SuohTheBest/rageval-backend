from fastapi import APIRouter, Response, Request, Cookie
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
    credential: str
    password: str


@router.post("/login")
async def login(r: LoginRequest, response: Response):
    try:
        usr = await utils.get_user_by_credential(r.credential, r.password)
        if usr is None:
            return {"success": False, "message": "User not found."}
        jwt_str = access_token.create_access_token(str(usr.id))
        response.set_cookie(
            key="access_token",
            value=jwt_str,
            httponly=True,
            max_age=access_token.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            # secure=True,
        )
        return {"success": True, "name": usr.username, "avatar": usr.avatar}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/reset-password")
async def register(r: RegisterRequest):
    try:
        result = await utils.renew_password(r.username, r.email, r.password)
        return {"success": result}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/me")
async def me(r: Request):
    try:
        cookie = r.cookies
        if len(cookie) == 0:
            return {"success": False, "message": "Cookie not found."}
        jwt = cookie.get("access_token")
        if jwt is None:
            return {"success": False, "message": "Not logged in."}
        usr = await access_token.get_current_user(jwt)
        return {"success": True, "id": usr.id, "name": usr.username, "avatar": usr.avatar, "role": usr.role}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/get-access-token")
async def get_access_token(access_token: str = Cookie(None)):
    if access_token is None:
        return {"success": False, "message": "Not logged in."}
    else:
        return {"success": True, "access_token": access_token}
