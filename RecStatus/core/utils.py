import aiohttp, asyncio
from typing import Dict, Optional

from core.logs import log_print

async def check_server_status(url: str) -> bool:
    """检查服务器状态"""
    try:
        timeout = aiohttp.ClientTimeout(total=5, connect=2) 
        async with aiohttp.ClientSession(trust_env=False, timeout=timeout) as session:
            async with session.get(url) as response:
                return response.status < 400 
    except asyncio.TimeoutError:
        log_print(f"检查服务器 {url} 超时", "DEBUG")
        return False
    except aiohttp.ClientError as e:
        log_print(f"检查服务器 {url} 连接错误: {type(e).__name__}", "DEBUG")
        return False
    except Exception as e:
        log_print(f"检查服务器 {url} 发生未知错误: {e}", "ERROR")
        return False

def handle_operation_error(operation: str, recType: str, recName: Optional[str] = None, user: Optional[str] = None) -> str:
    """处理操作失败的错误消息"""
    base_msg = f"{operation}失败"
    user_info = f"用户 {user} " if user else ""
    if recName:
        return f"{user_info}在{recType}录播机 {recName} 中{base_msg}"
    return f"{user_info}{base_msg}"

def get_server_display_host(api_info: Dict, rec_type: str, config: Dict) -> str:
    """
    获取显示用的服务器地址，考虑URL_HIDDEN配置
    
    :param api_info: API配置信息
    :param rec_type: 录播机类型 (recheme 或 blrec)
    :param config: 全局配置字典
    :return: 显示用的地址，如果URL_HIDDEN为True则返回"已隐藏"
    """
    host = api_info.get("URL", "").rstrip('/')
    url_hidden = api_info.get("URL_HIDDEN", 
                            config.get(rec_type.upper(), {}).get("URL_HIDDEN", False))
    return "已隐藏" if url_hidden else host 