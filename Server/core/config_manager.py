from ruamel.yaml import YAML
from typing import Dict

from core.logs import log_print

CONFIG_FILE = "config.yaml"

def load_config() -> Dict:
    """加载配置文件并应用默认值"""
    try:
        yaml = YAML()
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.load(f)
            
        if config is None:
            config = {}
            log_print(f"配置文件 {CONFIG_FILE} 为空或格式错误，将使用默认值创建。", "WARNING")
            
        if "AUTH" not in config:
            config["AUTH"] = {}
            
        if not isinstance(config["AUTH"], dict):
            log_print("配置文件中的 AUTH 必须是一个字典，已重置为默认值。", "WARNING")
            config["AUTH"] = {}
            
        auth_defaults = {
            "ENABLE": False,
            "AUTH_KEY": "114514",
            "AUTH_KEY_EXPIRE": 60 * 24,
            "AUTH_USER": {}
        }
        for key, default_value in auth_defaults.items():
            if key not in config["AUTH"]:
                config["AUTH"][key] = default_value

        top_level_defaults = {
            "HOST": "127.0.0.1",
            "PORT": 8080,
            "RECHEME": {},
            "BLREC": {}
        }
        for key, default_value in top_level_defaults.items():
            if key not in config:
                config[key] = default_value

        return config
        
    except FileNotFoundError:
        log_print(f"配置文件 {CONFIG_FILE} 未找到，将创建并使用默认值。", "WARNING")
        default_config = {}
        top_level_defaults = {
            "HOST": "127.0.0.1",
            "PORT": 8080,
            "RECHEME": {},
            "BLREC": {},
            "AUTH": {
                "ENABLE": False,
                "AUTH_KEY": "114514",
                "AUTH_KEY_EXPIRE": 60 * 24,
                "AUTH_USER": {}
            }
        }
        return default_config
        
    except Exception as e:
        log_print(f"加载配置文件 {CONFIG_FILE} 失败: {e}", "ERROR")
        raise

def save_config(config: Dict):
    """保存配置到文件"""
    try:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            yaml.dump(config, file)
            log_print(f"[配置] 配置文件 {CONFIG_FILE} 保存成功")
        return True
    except Exception as e:
        log_print(f"[配置] 保存配置文件 {CONFIG_FILE} 失败: {e}", "ERROR")
        return False 