from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING
from fastapi import Depends

if TYPE_CHECKING:
    from core.services.auth import Auth
    from core.services.cookie_manager import CookieManager

# 全局对象
_config: dict[str, Any] | None = None
_logger: logging.Logger | None = None
_auth: Auth | None = None
_cookie_manager: CookieManager | None = None

def setup_dependencies(
    config: dict[str, Any],
    logger: logging.Logger,
    auth: Auth,
    cookie_manager: CookieManager
) -> None:
    """设置全局依赖对象，在应用启动时由 lifespan 函数调用"""
    global _config, _logger, _auth, _cookie_manager
    _config = config
    _logger = logger
    _auth = auth
    _cookie_manager = cookie_manager

def get_config() -> dict[str, Any]:
    """获取配置对象"""
    if _config is None:
        raise RuntimeError("全局配置尚未初始化")
    return _config

def get_logger() -> logging.Logger:
    """获取日志记录器"""
    if _logger is None:
        raise RuntimeError("日志服务尚未初始化")
    return _logger

def get_auth() -> Auth:
    """获取认证服务对象"""
    if _auth is None:
        raise RuntimeError("认证服务尚未初始化")
    return _auth

def get_cookie_manager() -> CookieManager:
    """获取Cookie管理器对象"""
    if _cookie_manager is None:
        raise RuntimeError("Cookie 管理器尚未初始化")
    return _cookie_manager

# 组合依赖
def get_common_dependencies(
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
) -> dict[str, Any]:
    """获取常用依赖组合 (配置和日志)"""
    return {
        "config": config,
        "logger": logger
    }

def get_full_dependencies(
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger),
    auth: Auth = Depends(get_auth),
    cookie_manager: CookieManager = Depends(get_cookie_manager)
) -> dict[str, Any]:
    """获取所有依赖"""
    return {
        "config": config,
        "logger": logger,
        "auth": auth,
        "cookie_manager": cookie_manager
    }
