from __future__ import annotations

from typing import Dict, TYPE_CHECKING
from fastapi import Depends

from core.logs import log
if TYPE_CHECKING:
    from core.services.auth import Auth
    from core.services.cookie_manager import CookieManager

# 全局对象
_config: Dict = None
_logger = None
_auth: Auth = None 
_cookie_manager: CookieManager = None

def setup_dependencies(config: Dict, logger, auth: Auth, cookie_manager: CookieManager):
    """设置全局依赖对象，在应用启动时由 lifespan 函数调用"""
    global _config, _logger, _auth, _cookie_manager
    _config = config
    _logger = logger
    _auth = auth
    _cookie_manager = cookie_manager

def get_config():
    """获取配置对象"""
    return _config

def get_logger():
    """获取日志记录器"""
    return _logger

def get_auth() -> Auth:
    """获取认证服务对象"""
    return _auth

def get_cookie_manager() -> CookieManager:
    """获取Cookie管理器对象"""
    return _cookie_manager

# 组合依赖
def get_common_dependencies(
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """获取常用依赖组合 (配置和日志)"""
    return {
        "config": config,
        "logger": logger
    }

def get_full_dependencies(
    config: Dict = Depends(get_config),
    logger = Depends(get_logger),
    auth: Auth = Depends(get_auth),
    cookie_manager: CookieManager = Depends(get_cookie_manager)
):
    """获取所有依赖"""
    return {
        "config": config,
        "logger": logger,
        "auth": auth,
        "cookie_manager": cookie_manager
    } 