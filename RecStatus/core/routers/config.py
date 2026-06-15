from copy import deepcopy
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from core.config_manager import save_config
from core.dependencies import get_auth, get_config, get_cookie_manager, get_logger
from core.services.auth import get_current_user

router = APIRouter()

SENSITIVE_KEYS = {"AUTH_KEY", "PASS", "TOKEN", "BASIC_PASS", "BASIC_KEY"}


def _require_dict(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail=f"{name} 必须是对象")
    return value


def _strip_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_sensitive(child)
            for key, child in value.items()
            if key not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_strip_sensitive(item) for item in value]
    return value


def _global_section(section: Any) -> Dict[str, Any]:
    if not isinstance(section, dict):
        return {}
    return {key: value for key, value in section.items() if not isinstance(value, list)}


def _public_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return _strip_sensitive({
        "HOST": config.get("HOST", "0.0.0.0"),
        "PORT": config.get("PORT", 11111),
        "AUTH": config.get("AUTH", {}),
        "COOKIE": config.get("COOKIE", {}),
        "RECHEME": _global_section(config.get("RECHEME", {})),
        "BLREC": _global_section(config.get("BLREC", {}))
    })


def _merge_dict(current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(current)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _merge_cookie_config(current: Any, incoming: Any) -> Dict[str, Any]:
    current_config = current if isinstance(current, dict) else {}
    incoming_config = _require_dict(incoming, "COOKIE")
    result: Dict[str, Any] = {"ENABLE": bool(incoming_config.get("ENABLE", current_config.get("ENABLE", False)))}
    incoming_blocks = {
        key: value
        for key, value in incoming_config.items()
        if key != "ENABLE" and isinstance(value, dict)
    }

    if not incoming_blocks:
        for key, value in current_config.items():
            if key != "ENABLE":
                result[key] = deepcopy(value)
        return result

    for key, value in incoming_blocks.items():
        result[key] = _merge_dict(current_config.get(key, {}), value)
    return result


def _apply_auth(config: Dict[str, Any], incoming: Any) -> None:
    incoming_auth = _require_dict(incoming, "AUTH")
    auth_config = deepcopy(config.get("AUTH", {})) if isinstance(config.get("AUTH"), dict) else {}

    if "ENABLE" in incoming_auth:
        auth_config["ENABLE"] = bool(incoming_auth["ENABLE"])
    if "AUTH_KEY" in incoming_auth:
        auth_config["AUTH_KEY"] = str(incoming_auth["AUTH_KEY"])
    if "AUTH_KEY_EXPIRE" in incoming_auth:
        try:
            expire_minutes = int(incoming_auth["AUTH_KEY_EXPIRE"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="AUTH_KEY_EXPIRE 必须是整数")
        if expire_minutes <= 0:
            raise HTTPException(status_code=400, detail="AUTH_KEY_EXPIRE 必须大于 0")
        auth_config["AUTH_KEY_EXPIRE"] = expire_minutes

    if "AUTH_USER" in incoming_auth:
        incoming_users = _require_dict(incoming_auth["AUTH_USER"], "AUTH_USER")
        old_users = auth_config.get("AUTH_USER", {})
        if not isinstance(old_users, dict):
            old_users = {}

        users: Dict[str, Dict[str, str]] = {}
        for display_name, user_data in incoming_users.items():
            user_config = _require_dict(user_data, f"AUTH_USER.{display_name}")
            old_user_config = old_users.get(display_name, {})
            if not isinstance(old_user_config, dict):
                old_user_config = {}

            user_name = user_config.get("USER", old_user_config.get("USER", display_name))
            next_user = {"USER": str(user_name)}
            if "PASS" in user_config:
                next_user["PASS"] = str(user_config["PASS"])
            elif "PASS" in old_user_config:
                next_user["PASS"] = str(old_user_config["PASS"])
            else:
                next_user["PASS"] = ""
            users[str(display_name)] = next_user
        auth_config["AUTH_USER"] = users

    config["AUTH"] = auth_config


def _apply_global_section(config: Dict[str, Any], name: str, incoming: Any) -> None:
    incoming_section = _require_dict(incoming, name)
    current_section = config.get(name, {})
    if not isinstance(current_section, dict):
        current_section = {}

    instance_items = {
        key: deepcopy(value)
        for key, value in current_section.items()
        if isinstance(value, list)
    }
    current_globals = _global_section(current_section)
    next_globals = _merge_dict(current_globals, incoming_section)
    if "COOKIE" in incoming_section:
        next_globals["COOKIE"] = _merge_cookie_config(
            current_globals.get("COOKIE", {}),
            incoming_section["COOKIE"]
        )

    config[name] = {}
    config[name].update(next_globals)
    config[name].update(instance_items)


def _apply_payload(config: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    old_host = config.get("HOST", "0.0.0.0")
    old_port = int(config.get("PORT", 11111))

    if "HOST" in payload:
        host = str(payload["HOST"]).strip()
        if not host:
            raise HTTPException(status_code=400, detail="HOST 不能为空")
        config["HOST"] = host

    if "PORT" in payload:
        try:
            port = int(payload["PORT"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="PORT 必须是整数")
        if port < 1 or port > 65535:
            raise HTTPException(status_code=400, detail="PORT 必须在 1 到 65535 之间")
        config["PORT"] = port

    if "AUTH" in payload:
        _apply_auth(config, payload["AUTH"])
    if "COOKIE" in payload:
        config["COOKIE"] = _merge_cookie_config(config.get("COOKIE", {}), payload["COOKIE"])
    if "RECHEME" in payload:
        _apply_global_section(config, "RECHEME", payload["RECHEME"])
    if "BLREC" in payload:
        _apply_global_section(config, "BLREC", payload["BLREC"])

    return config.get("HOST") != old_host or int(config.get("PORT", 11111)) != old_port


@router.get("/config")
async def get_system_config(
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config)
):
    """获取脱敏后的系统配置"""
    return {
        "config": _public_config(config),
        "restartRequired": False
    }


@router.put("/config")
async def update_system_config(
    payload: Dict[str, Any],
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    auth=Depends(get_auth),
    cookie_manager=Depends(get_cookie_manager),
    logger=Depends(get_logger)
):
    """更新系统全局配置"""
    logger.debug(f"[配置] 用户 {current_user} 请求更新系统配置")
    original_config = deepcopy(config)
    saved = False
    try:
        restart_required = _apply_payload(config, _require_dict(payload, "请求体"))
        if not save_config(config):
            config.clear()
            config.update(original_config)
            raise HTTPException(status_code=500, detail="保存配置文件失败")
        saved = True

        if auth:
            auth.reload(config)
        if cookie_manager:
            await cookie_manager.reload(config)

        return {
            "success": True,
            "restartRequired": restart_required,
            "message": "配置已保存",
            "config": _public_config(config)
        }
    except HTTPException:
        if not saved:
            config.clear()
            config.update(original_config)
        raise
    except Exception as e:
        if not saved:
            config.clear()
            config.update(original_config)
        logger.error(f"[配置] 更新系统配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新系统配置失败: {e}")
