import re
from ruamel.yaml import YAML
from typing import Dict
from io import StringIO

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
        yaml.width = 1000
        yaml.indent(mapping=2, sequence=4, offset=2)
        buf = StringIO()
        yaml.dump(config, buf)
        content = buf.getvalue()
        
        # 修复格式
        content = re.sub(r'-\s*\n\s+', '- ', content)
        
        # 空行处理
        lines = content.splitlines()
        formatted_lines = []
        in_recheme = False
        prev_line_is_rec_item = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip() == "RECHEME:":
                in_recheme = True
                formatted_lines.append(line)
                i += 1
                continue
                
            if in_recheme and line and not line.startswith(" ") and line.endswith(":"):
                in_recheme = False
                
                if formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append("")
                    formatted_lines.append("")
                elif formatted_lines and not formatted_lines[-1].strip():
                    formatted_lines.append("")
                
                formatted_lines.append(line)
                i += 1
                continue
            
            # 处理RECHEME内部
            if in_recheme:
                if line.startswith("  ") and line.strip().endswith(":"):
                    if prev_line_is_rec_item:
                        while i > 0 and i < len(formatted_lines) and not formatted_lines[-1].strip():
                            formatted_lines.pop()
                    
                    formatted_lines.append(line)
                    prev_line_is_rec_item = True
                    i += 1
                    continue
                
                if line.strip():
                    formatted_lines.append(line)
                    i += 1
                    if not (line.startswith("  ") and line.strip().endswith(":")):
                        prev_line_is_rec_item = False
                    continue
                
                if not line.strip():
                    next_is_rec_item = False
                    if i+1 < len(lines):
                        next_line = lines[i+1]
                        if next_line.startswith("  ") and next_line.strip().endswith(":"):
                            next_is_rec_item = True
                    
                    if next_is_rec_item:
                        i += 1
                        continue
                    else:
                        formatted_lines.append(line)
                        i += 1
                        continue
            else:
                formatted_lines.append(line)
                i += 1
                prev_line_is_rec_item = False
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            file.write("\n".join(formatted_lines))
            log_print(f"[配置] 配置文件 {CONFIG_FILE} 保存成功")
        return True
    except Exception as e:
        log_print(f"[配置] 保存配置文件 {CONFIG_FILE} 失败: {e}", "ERROR")
        return False 