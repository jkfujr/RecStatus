from fastapi import APIRouter, HTTPException, Depends
from typing import Dict

from core.dependencies import get_config, get_auth
from core.models import LoginRequest

router = APIRouter()

@router.get("/login")
async def check_auth_status(config: Dict = Depends(get_config)):
    """
    检查认证状态
    当AUTH.ENABLE为false时，返回无需认证的提示
    当AUTH.ENABLE为true时，返回需要认证的提示
    """
    auth_config = config.get("AUTH", {})
    auth_enabled = auth_config.get("ENABLE", False)
    return {
        "message": "需要登录" if auth_enabled else "认证未启用，无需登录",
        "auth_required": auth_enabled
    }

@router.post("/login")
async def login(
    request: LoginRequest,
    config: Dict = Depends(get_config),
    auth = Depends(get_auth)
):
    """用户登录"""
    username = request.username
    password = request.password
    auth_config = config.get("AUTH", {})
    auth_enabled = auth_config.get("ENABLE", False)

    if not auth_enabled:
        return {
            "message": "认证未启用，无需登录",
            "token": None,
            "auth_required": False
        }
        
    if not auth:
         raise HTTPException(status_code=500, detail="认证服务未初始化")

    if auth.authenticate_user(username, password):
        token = auth.create_token(username)
        return {
            "message": "登录成功",
            "token": token,
            "auth_required": True
        }
    
    raise HTTPException(
        status_code=401,
        detail="用户名或密码错误"
    ) 