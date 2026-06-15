from typing import Dict
from core.external.recheme import RechemeAPI
from core.external.blrec import BLRECAPI

def create_recheme_instance(api_info: Dict, rec_name: str, config: Dict) -> RechemeAPI:
    """
    创建录播姬 API 实例
    
    :param api_info: API配置信息
    :param rec_name: 实例名称
    :param config: 全局配置字典
    :return: RechemeAPI实例
    """
    host = api_info.get("URL", "").rstrip('/')
    manage = api_info.get("MANAGE", True)
    
    basic_auth = api_info.get("BASIC", config.get("RECHEME", {}).get("BASIC", False))
    username = api_info.get("BASIC_USER", config.get("RECHEME", {}).get("BASIC_USER", ""))
    password = api_info.get("BASIC_PASS", config.get("RECHEME", {}).get("BASIC_PASS", ""))
    
    return RechemeAPI(
        host=host,
        name=rec_name,
        basic_auth=basic_auth,
        username=username,
        password=password,
        manage=manage
    )

def create_blrec_instance(api_info: Dict, name: str, config: Dict) -> BLRECAPI:
    """
    创建 BLREC API 实例
    
    :param api_info: API配置信息
    :param name: 实例名称
    :param config: 全局配置字典
    :return: BLRECAPI实例
    """
    host = api_info.get("URL", "").rstrip('/')
    manage = api_info.get("MANAGE", True)
    
    basic_auth = api_info.get("BASIC", config.get("BLREC", {}).get("BASIC", True))
    api_key = api_info.get("BASIC_KEY", config.get("BLREC", {}).get("BASIC_KEY", "bili2233"))
    
    return BLRECAPI(
        host=host,
        name=name,
        api_key=api_key if basic_auth else "",
        manage=manage
    ) 