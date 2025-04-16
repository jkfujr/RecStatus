"""API 辅助函数模块，用于简化服务器操作和抽象常见模式"""

from typing import Dict, List, Any, Callable, Awaitable, Optional, Tuple, Union
import asyncio
from fastapi import HTTPException

from core.logs import log
from core.utils import get_server_display_host, handle_operation_error
from core.external.factory import create_recheme_instance, create_blrec_instance

logger = log()

async def iterate_server_instances(
    config: Dict,
    operation: Callable[[Any, str, str, Dict], Awaitable[Any]],
    rec_type: Optional[str] = None,
    rec_name: Optional[str] = None,
    current_user: Optional[str] = None,
    operation_name: str = "操作",
    api_params: Optional[Dict] = None
) -> List[Dict]:
    """
    遍历服务器实例并对每个实例执行指定操作。
    
    Args:
        config: 全局配置
        operation: 要执行的异步操作函数，接收 API 实例、rec_name、rec_type 和 api_info 参数
        rec_type: 可选，限制操作到特定类型的录播机 ("recheme" 或 "blrec")
        rec_name: 可选，限制操作到特定名称的录播机
        current_user: 执行操作的用户，用于日志记录
        operation_name: 操作名称，用于日志和错误消息
        api_params: 传递给操作函数的额外参数
    
    Returns:
        List[Dict]: 成功执行操作的实例结果列表
    """
    if api_params is None:
        api_params = {}
        
    success_results = []

    if (not rec_type or rec_type == "recheme") and "RECHEME" in config:
        for name, api_info_list in config["RECHEME"].items():
            if rec_name and name != rec_name:
                continue
                
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    try:
                        recheme = create_recheme_instance(api_info, name, config)
                        result = await operation(recheme, name, "recheme", api_info, **api_params)
                        if result is not None:
                            if isinstance(result, dict) and "recServer" in result:
                                display_host = get_server_display_host(api_info, "recheme", config)
                                result["recServer"]["recHost"] = display_host
                            elif isinstance(result, list):
                                display_host = get_server_display_host(api_info, "recheme", config)
                                for item in result:
                                    if isinstance(item, dict) and "recServer" in item:
                                        item["recServer"]["recHost"] = display_host

                            if isinstance(result, list):
                                success_results.extend(result)
                            else:
                                success_results.append(result)
                    except Exception as e:
                        logger.error(f"[API] Recheme {name} {operation_name}失败: {str(e)}")

    if (not rec_type or rec_type == "blrec") and "BLREC" in config:
        for name, api_info_list in config["BLREC"].items():
            if rec_name and name != rec_name:
                continue
                
            if isinstance(api_info_list, list) and name not in ["BLREC_BASIC", "BLREC_BASIC_KEY"]:
                for api_info in api_info_list:
                    try:
                        blrec = create_blrec_instance(api_info, name, config)
                        result = await operation(blrec, name, "blrec", api_info, **api_params)
                        if result is not None:
                            if isinstance(result, dict) and "recServer" in result:
                                display_host = get_server_display_host(api_info, "blrec", config)
                                result["recServer"]["recHost"] = display_host
                            elif isinstance(result, list):
                                display_host = get_server_display_host(api_info, "blrec", config)
                                for item in result:
                                    if isinstance(item, dict) and "recServer" in item:
                                        item["recServer"]["recHost"] = display_host
                            
                            if isinstance(result, list):
                                success_results.extend(result)
                            else:
                                success_results.append(result)
                    except Exception as e:
                        logger.error(f"[API] BLREC {name} {operation_name}失败: {str(e)}")

    if not success_results:
        error_msg = handle_operation_error(operation_name, rec_type or "所有", rec_name, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return success_results

async def parallel_iterate_server_instances(
    config: Dict,
    operation: Callable[[Any, str, str, Dict], Awaitable[Any]],
    rec_type: Optional[str] = None,
    rec_name: Optional[str] = None,
    current_user: Optional[str] = None,
    operation_name: str = "操作",
    api_params: Optional[Dict] = None
) -> List[Dict]:
    """
    并行遍历服务器实例并对每个实例执行指定操作。
    
    与 iterate_server_instances 类似，但使用 asyncio.gather 并行执行操作。
    适用于独立的操作，例如获取状态或统计信息，不适用于需要事务或幂等性的操作。
    
    Args:
        参数与 iterate_server_instances 相同
    
    Returns:
        List[Dict]: 成功执行操作的实例结果列表
    """
    if api_params is None:
        api_params = {}
        
    tasks = []
    task_info = []
    
    if (not rec_type or rec_type == "recheme") and "RECHEME" in config:
        for name, api_info_list in config["RECHEME"].items():
            if rec_name and name != rec_name:
                continue
                
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    try:
                        recheme = create_recheme_instance(api_info, name, config)
                        task = operation(recheme, name, "recheme", api_info, **api_params)
                        tasks.append(task)
                        task_info.append((name, "recheme", api_info))
                    except Exception as e:
                        logger.error(f"[API] 创建 Recheme {name} 任务失败: {str(e)}")
    
    if (not rec_type or rec_type == "blrec") and "BLREC" in config:
        for name, api_info_list in config["BLREC"].items():
            if rec_name and name != rec_name:
                continue
                
            if isinstance(api_info_list, list) and name not in ["BLREC_BASIC", "BLREC_BASIC_KEY"]:
                for api_info in api_info_list:
                    try:
                        blrec = create_blrec_instance(api_info, name, config)
                        task = operation(blrec, name, "blrec", api_info, **api_params)
                        tasks.append(task)
                        task_info.append((name, "blrec", api_info))
                    except Exception as e:
                        logger.error(f"[API] 创建 BLREC {name} 任务失败: {str(e)}")
    
    if not tasks:
        error_msg = handle_operation_error(operation_name, rec_type or "所有", rec_name, current_user)
        logger.error(f"[API] {error_msg} - 未创建任何任务")
        raise HTTPException(status_code=500, detail=error_msg)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            name, type_, api_info = task_info[i]
            logger.error(f"[API] {type_} {name} {operation_name}失败: {str(result)}")
            continue
            
        if result is not None:
            name, type_, api_info = task_info[i]
            
            if isinstance(result, dict) and "recServer" in result:
                display_host = get_server_display_host(api_info, type_, config)
                result["recServer"]["recHost"] = display_host
            elif isinstance(result, list):
                display_host = get_server_display_host(api_info, type_, config)
                for item in result:
                    if isinstance(item, dict) and "recServer" in item:
                        item["recServer"]["recHost"] = display_host

            if isinstance(result, list):
                success_results.extend(result)
            else:
                success_results.append(result)

    if not success_results:
        error_msg = handle_operation_error(operation_name, rec_type or "所有", rec_name, current_user)
        logger.error(f"[API] {error_msg} - 所有并行任务都失败了")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return success_results 