import json
import os
import secrets
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.logs import log_print
from core.paths import CONFIG_FILE, DATA_DIR, LEGACY_CONFIG_FILE


def _random_secret(length: int = 32) -> str:
    """生成适合配置文件使用的随机密钥。"""
    return secrets.token_urlsafe(length)


def create_default_config() -> tuple[Dict[str, Any], str]:
    """创建首次启动默认配置，并返回初始管理员密码。"""
    initial_password = _random_secret(18)
    config = {
        "HOST": "0.0.0.0",
        "PORT": 11111,
        "AUTH": {
            "ENABLE": True,
            "AUTH_KEY": _random_secret(32),
            "AUTH_KEY_EXPIRE": 1919810,
            "AUTH_USER": {
                "admin": {
                    "USER": "admin",
                    "PASS": initial_password
                }
            }
        },
        "COOKIE": {
            "ENABLE": False
        },
        "RECHEME": {},
        "BLREC": {}
    }
    return config, initial_password


def apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """补齐运行所需的最小默认配置。"""
    if not isinstance(config, dict):
        raise ValueError("配置顶层必须是对象")

    config.setdefault("HOST", "0.0.0.0")
    config.setdefault("PORT", 11111)

    auth_config = config.setdefault("AUTH", {})
    if not isinstance(auth_config, dict):
        log_print("配置中的 AUTH 必须是对象，已重置为空对象。", "WARNING")
        auth_config = {}
        config["AUTH"] = auth_config
    auth_config.setdefault("ENABLE", True)
    auth_config.setdefault("AUTH_KEY", "114514")
    auth_config.setdefault("AUTH_KEY_EXPIRE", 1919810)
    if not isinstance(auth_config.get("AUTH_USER"), dict):
        auth_config["AUTH_USER"] = {}

    for section in ("COOKIE", "RECHEME", "BLREC"):
        section_config = config.setdefault(section, {})
        if not isinstance(section_config, dict):
            log_print(f"配置中的 {section} 必须是对象，已重置为空对象。", "WARNING")
            config[section] = {}

    return config


def _normalize_legacy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """迁移时一次性规范化旧字段名。"""
    normalized = deepcopy(config)
    blrec_config = normalized.get("BLREC")
    if isinstance(blrec_config, dict):
        if "BLREC_BASIC" in blrec_config and "BASIC" not in blrec_config:
            blrec_config["BASIC"] = blrec_config["BLREC_BASIC"]
        if "BLREC_BASIC_KEY" in blrec_config and "BASIC_KEY" not in blrec_config:
            blrec_config["BASIC_KEY"] = blrec_config["BLREC_BASIC_KEY"]
        blrec_config.pop("BLREC_BASIC", None)
        blrec_config.pop("BLREC_BASIC_KEY", None)
    return normalized


def _backup_legacy_config() -> Path:
    backup_path = LEGACY_CONFIG_FILE.with_suffix(LEGACY_CONFIG_FILE.suffix + ".bak")
    if backup_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = LEGACY_CONFIG_FILE.with_suffix(LEGACY_CONFIG_FILE.suffix + f".{timestamp}.bak")
    LEGACY_CONFIG_FILE.rename(backup_path)
    return backup_path


def _load_json_config() -> Dict[str, Any]:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)
    return apply_defaults(config)


def _load_legacy_yaml() -> Dict[str, Any]:
    try:
        from ruamel.yaml import YAML
    except ImportError as e:
        raise RuntimeError("迁移 YAML 配置需要安装 ruamel.yaml") from e

    yaml = YAML(typ="safe")
    with LEGACY_CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = yaml.load(file)
    if not isinstance(config, dict):
        raise ValueError(f"旧配置文件 {LEGACY_CONFIG_FILE} 的顶层必须是对象")
    return apply_defaults(_normalize_legacy_config(config))


def _write_json_config(config: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = CONFIG_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)
        file.write("\n")
    os.replace(temp_file, CONFIG_FILE)


def _migrate_legacy_config() -> Dict[str, Any]:
    config = _load_legacy_yaml()
    _write_json_config(config)
    backup_path = _backup_legacy_config()
    log_print(f"[配置] 已迁移 {LEGACY_CONFIG_FILE} 到 {CONFIG_FILE}")
    log_print(f"[配置] 旧配置已备份为 {backup_path}")
    return config


def _create_default_config_file() -> Dict[str, Any]:
    config, initial_password = create_default_config()
    _write_json_config(config)
    log_print(f"[配置] 未找到配置文件，已创建默认配置: {CONFIG_FILE}")
    log_print("[配置] 首次启动默认管理员账号：admin")
    log_print(f"[配置] 首次启动默认管理员密码：{initial_password}")
    return config


def load_config() -> Dict[str, Any]:
    """加载配置；运行态只读取 JSON，YAML 仅用于一次性迁移。"""
    try:
        if CONFIG_FILE.exists():
            return _load_json_config()
        if LEGACY_CONFIG_FILE.exists():
            return _migrate_legacy_config()
        return _create_default_config_file()
    except Exception as e:
        log_print(f"加载配置失败: {e}", "ERROR")
        raise


def save_config(config: Dict[str, Any]) -> bool:
    """保存配置到 JSON 文件。"""
    try:
        _write_json_config(apply_defaults(config))
        log_print(f"[配置] 配置文件 {CONFIG_FILE} 保存成功")
        return True
    except Exception as e:
        log_print(f"[配置] 保存配置文件 {CONFIG_FILE} 失败: {e}", "ERROR")
        return False
