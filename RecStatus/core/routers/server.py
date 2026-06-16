from fastapi import APIRouter, Depends, HTTPException
from typing import Any, List, Union, Optional
import asyncio, copy, logging

from core.dependencies import get_config, get_logger
from core.models import (
    RecServerInfo, AddServerRequest, BatchAddServerRequest,
    DeleteServerRequest, BatchDeleteServerRequest
)
from core.services.auth import get_current_user
from core.external.factory import create_recheme_instance, create_blrec_instance
from core.utils import get_server_display_host
from core.config_manager import save_config

router = APIRouter()

# === 辅助函数 ===

async def _fetch_single_server_info(
    rec_type: str,
    rec_name: str,
    api_info: dict[str, Any],
    config: dict[str, Any],
    logger: logging.Logger
) -> Optional[RecServerInfo]:
    """获取单个录播机实例的状态和统计信息"""
    instance = None
    rooms_data = None
    status = "offline"

    try:
        if rec_type == "recheme":
            instance = create_recheme_instance(api_info, rec_name, config)
            rooms_data = await instance.get_rooms()
        elif rec_type == "blrec":
            instance = create_blrec_instance(api_info, rec_name, config)
            rooms_data = await instance.get_rooms()
        else:
            logger.error(f"[Server Status] 未知的录播机类型: {rec_type} for {rec_name}")
            return None
        if rooms_data is not None:
            status = "online"
        else:
            status = "offline"
            logger.warning(f"[Server Status] {rec_name} ({rec_type}) 离线或 API 调用失败")
            rooms_data = []

    except Exception as e:
        status = "error"
        logger.error(f"[Server Status] 检查 {rec_name} ({rec_type}) 时出错: {e}", exc_info=True)
        rooms_data = []

    total = 0
    streaming = 0
    recording = 0
    
    if status == "online" and isinstance(rooms_data, list):
        total = len(rooms_data)
        for room in rooms_data:
            if not isinstance(room, dict): continue

            if rec_type == "recheme":
                if room.get("streaming", False):
                    streaming += 1
                if room.get("recording", False):
                    recording += 1
            elif rec_type == "blrec":
                if room.get("room_info", {}).get("live_status", 0) == 1:
                    streaming += 1
                task_status = room.get("task_status", {})
                if isinstance(task_status, dict) and task_status.get("running_status") == "recording":
                    recording += 1

    display_host = get_server_display_host(api_info, rec_type, config)
    manage = api_info.get("MANAGE", True)
    
    return RecServerInfo(
        recName=rec_name,
        recType=rec_type,
        recHost=display_host,
        recStatus=status,
        recManage=manage,
        totalRooms=total,
        streamingRooms=streaming,
        recordingRooms=recording
    )

def _summarize_server_results(servers_info: List[RecServerInfo], logger: logging.Logger) -> None:
    """汇总服务器检查结果并记录日志"""
    total_servers = len(servers_info)
    online_servers = sum(1 for s in servers_info if s.recStatus == "online")
    offline_servers = sum(1 for s in servers_info if s.recStatus == "offline")
    error_servers = sum(1 for s in servers_info if s.recStatus == "error")
    
    total_rooms = sum(s.totalRooms for s in servers_info)
    streaming_rooms = sum(s.streamingRooms for s in servers_info)
    recording_rooms = sum(s.recordingRooms for s in servers_info)

    logger.debug(f"[Server Status] 服务器状态汇总: {online_servers}个在线, {offline_servers}个离线, {error_servers}个错误")
    logger.debug(f"[Server Status] 房间数据汇总: 共{total_rooms}个房间, {streaming_rooms}个直播中, {recording_rooms}个录制中")
    empty_servers = [s.recName for s in servers_info if s.recStatus == "online" and s.totalRooms == 0]
    if empty_servers:
        logger.debug(f"[Server Status] 没有房间数据的服务器: {', '.join(empty_servers)}")

async def get_all_recservers(config: dict[str, Any], logger: logging.Logger) -> List[RecServerInfo]:
    """获取所有录播机信息"""
    if not config:
        logger.error("[Server Status] 配置未提供，无法获取服务器列表")
        return []

    tasks: list[Any] = []
    server_names: dict[str, list[str]] = {"recheme": [], "blrec": []}
    
    recheme_config = config.get("RECHEME", {})
    if isinstance(recheme_config, dict):
        for rec_name, api_info_list in recheme_config.items():
            if isinstance(api_info_list, list):
                server_names["recheme"].append(rec_name)
                for api_info in api_info_list:
                    if isinstance(api_info, dict):
                        tasks.append(
                            _fetch_single_server_info("recheme", rec_name, api_info, config, logger)
                        )

    blrec_config = config.get("BLREC", {})
    if isinstance(blrec_config, dict):
        for rec_name, api_info_list in blrec_config.items():
            if isinstance(api_info_list, list):
                server_names["blrec"].append(rec_name)
                for api_info in api_info_list:
                    if isinstance(api_info, dict):
                        tasks.append(
                            _fetch_single_server_info("blrec", rec_name, api_info, config, logger)
                        )

    if not tasks:
        logger.info("[Server Status] 配置中未找到有效的录播机实例")
        return []
    
    for rec_type, names in server_names.items():
        if names:
            logger.debug(f"[Server Status] 开始检查 {len(names)} 个 {rec_type} 实例: {', '.join(names)}")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    servers_info: List[RecServerInfo] = []
    for result in results:
        if isinstance(result, RecServerInfo):
            servers_info.append(result)
        elif isinstance(result, Exception):
            logger.error(f"[Server Status] 获取服务器信息时发生意外错误: {result}", exc_info=result)

    _summarize_server_results(servers_info, logger)
    
    logger.debug(f"[Server Status] 获取完成，共处理 {len(servers_info)} 个服务器实例")
    return servers_info

def _restore_config(config: dict[str, Any], snapshot: dict[str, Any]) -> None:
    config.clear()
    config.update(snapshot)

def _build_server_config(request: AddServerRequest) -> dict[str, Any]:
    server_config: dict[str, Any] = {"URL": request.url}
    
    if request.manage is not True:
        server_config["MANAGE"] = request.manage
    
    if request.url_hidden:
        server_config["URL_HIDDEN"] = True
    
    if request.recType == "recheme":
        if request.basic is not None:
            server_config["BASIC"] = request.basic
        if request.basicUser:
            server_config["BASIC_USER"] = request.basicUser
        if request.basicPass:
            server_config["BASIC_PASS"] = request.basicPass
    elif request.recType == "blrec":
        if request.basic is not None:
            server_config["BASIC"] = request.basic
        if request.basicKey:
            server_config["BASIC_KEY"] = request.basicKey
    
    return server_config

async def _add_single_server(
    request: AddServerRequest, 
    save_immediately: bool, 
    current_user: Optional[str],
    config: dict[str, Any],
    logger: logging.Logger
) -> dict[str, Any]:
    """添加单个录播机 (使用依赖注入的 config 和 logger)"""
    original_name = request.originalName or ""
    is_update = bool(original_name)
    operation_type = "更新" if is_update else "添加"
    
    logger.debug(f"[API] {'用户 ' + current_user + ' ' if current_user else ''}请求{operation_type}录播机: {request.recName} ({request.recType})")
    
    if request.recType not in ["recheme", "blrec"]:
        raise HTTPException(status_code=400, detail="不支持的录播类型，必须是 recheme 或 blrec")
    
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL 必须以 http:// 或 https:// 开头")
    
    config_key = request.recType.upper()
    section_value = config.get(config_key)
    server_section: dict[str, Any] = section_value if isinstance(section_value, dict) else {}
    
    if not is_update and request.recName in server_section:
        raise HTTPException(status_code=400, detail=f"{config_key} 录播机名称 {request.recName} 已存在")

    if is_update:
        if original_name not in server_section:
            raise HTTPException(status_code=404, detail=f"要更新的录播机 {original_name} 不存在")

        if original_name != request.recName and request.recName in server_section:
            raise HTTPException(status_code=400, detail=f"无法更新名称，{config_key} 录播机名称 {request.recName} 已存在")
    
    server_config = _build_server_config(request)
    snapshot = copy.deepcopy(config) if save_immediately else None

    if not isinstance(section_value, dict):
        config[config_key] = server_section
    
    if is_update and original_name != request.recName:
        del server_section[original_name]
    server_section[request.recName] = [server_config]
    
    if save_immediately and not save_config(config):
        logger.error(f"[API] {operation_type}服务器 {request.recName} 后保存配置文件失败，正在回滚...")
        if snapshot is not None:
            _restore_config(config, snapshot)
        logger.error(f"[API] {operation_type}服务器后保存配置文件失败，已回滚内存修改")
        raise HTTPException(status_code=500, detail="保存配置文件失败")
    
    display_host = get_server_display_host(server_config, request.recType, config)
    
    response_data = {
        "recName": request.recName,
        "recType": request.recType,
        "recHost": display_host,
        "recStatus": "未知",
        "recManage": request.manage
    }
    
    logger.debug(f"[API] 成功{operation_type}录播机: {request.recName}")
    return {"success": True, "data": response_data}

async def _delete_single_server(
    recName: str, 
    recType: str, 
    current_user: Optional[str],
    config: dict[str, Any],
    logger: logging.Logger
) -> dict[str, Any]:
    """删除单个录播机 (使用依赖注入的 config 和 logger)"""
    if not recName:
        raise HTTPException(status_code=400, detail="录播机名称不能为空")
    
    if recType not in ["recheme", "blrec"]:
        raise HTTPException(status_code=400, detail="不支持的录播机类型")
        
    config_key = recType.upper()
    section_value = config.get(config_key)
    if not isinstance(section_value, dict) or recName not in section_value:
        raise HTTPException(status_code=404, detail=f"{config_key} 服务器 {recName} 不存在")
    
    snapshot = copy.deepcopy(config)
    del section_value[recName]
    logger.info(f"[API] {'用户 ' + current_user + ' ' if current_user else ''}删除 {recType} 服务器 {recName} 成功 (内存)")

    if not save_config(config):
        _restore_config(config, snapshot)
        logger.error(f"[API] 删除服务器 {recName} 后保存配置文件失败，已回滚")
        raise HTTPException(status_code=500, detail="保存配置文件失败")

    return {
        "success": True,
        "message": f"已删除{recType}录播机 {recName}",
        "data": {
            "recName": recName,
            "recType": recType
        }
    }

# === API ===
@router.get("/server", response_model=List[RecServerInfo])
async def get_recservers(
    recName: Optional[str] = None,
    recType: Optional[str] = None,
    recStatus: Optional[str] = None,
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """获取所有录播机信息 (使用依赖注入的 logger)"""
    filters = []
    if recName: filters.append(f"名称={recName}")
    if recType: filters.append(f"类型={recType}")
    if recStatus: filters.append(f"状态={recStatus}")
    
    if filters:
        logger.debug(f"[API] 筛选录播机条件: {', '.join(filters)}")
    
    all_servers = await get_all_recservers(config, logger)
    
    filtered_servers = []
    for server in all_servers:
        if recName and server.recName != recName:
            continue
        if recType and server.recType != recType:
            continue
        if recStatus and server.recStatus != recStatus:
            continue
        filtered_servers.append(server)
    
    logger.debug(f"[API] 返回 {len(filtered_servers)} 个筛选后的录播机信息")
    return filtered_servers

@router.post("/server")
async def add_server(
    request: Union[AddServerRequest, BatchAddServerRequest],
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """添加录播机 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求添加录播机")
    
    if isinstance(request, BatchAddServerRequest):
        logger.debug(f"[API] 批量添加请求，共 {len(request.servers)} 个录播机")
        all_results: list[dict[str, Any]] = []
        failed_servers: list[dict[str, Any]] = []
        snapshot = copy.deepcopy(config)

        for server_req in request.servers:
            try:
                result = await _add_single_server(server_req, False, current_user, config, logger)
                all_results.append(result["data"])
            except HTTPException as e:
                failed_servers.append({
                    "recName": server_req.recName,
                    "recType": server_req.recType,
                    "error": e.detail
                })
                logger.error(f"[API] 批量添加: 录播机 {server_req.recName} 失败: {e.detail}")
        
        if all_results:
            if not save_config(config):
                logger.error("[API] 批量添加服务器后保存配置文件失败，正在回滚内存更改...")
                _restore_config(config, snapshot)
                logger.info("[API] 批量添加回滚完成")
                raise HTTPException(status_code=500, detail="保存配置文件失败")
            
        logger.debug(f"[API] 批量添加完成，成功: {len(all_results)}，失败: {len(failed_servers)}")
        return {
            "success": len(all_results) > 0,
            "total": len(request.servers),
            "succeeded": len(all_results),
            "failed": len(failed_servers),
            "data": all_results,
            "errors": failed_servers if failed_servers else None
        }
    elif isinstance(request, AddServerRequest):
        # 单个服务器添加
        return await _add_single_server(request, True, current_user, config, logger)
    else:
        raise HTTPException(status_code=400, detail="无效的请求格式")


@router.delete("/server")
async def delete_server(
    request: DeleteServerRequest,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """删除录播机 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求删除录播机服务器: {request.recName} ({request.recType})")
    return await _delete_single_server(request.recName, request.recType, current_user, config, logger)


@router.delete("/server/batch")
async def batch_delete_servers(
    request: BatchDeleteServerRequest,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """批量删除录播机 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求批量删除录播机服务器，共 {len(request.servers)} 个")
    
    all_results: list[dict[str, Any]] = []
    failed_servers: list[dict[str, Any]] = []
    deleted_server_keys: set[tuple[str, str]] = set()
    snapshot = copy.deepcopy(config)
    
    # 在内存中尝试删除
    for server_request in request.servers:
        config_key = server_request.recType.upper()
        recName = server_request.recName
        section_value = config.get(config_key)
        if isinstance(section_value, dict) and recName in section_value:
            del section_value[recName]
            deleted_server_keys.add((config_key, recName))
            logger.info(f"[API] 批量删除: {recName} ({server_request.recType}) 成功 (内存)")
        else:
            logger.warning(f"[API] 批量删除: 服务器 {recName} ({server_request.recType}) 在配置中未找到")
            failed_servers.append({
                "recName": recName,
                "recType": server_request.recType,
                "error": "服务器未找到"
            })

    # 如果有任何删除操作，尝试保存配置
    if deleted_server_keys: 
        if not save_config(config):
            logger.error("[API] 批量删除服务器后保存配置文件失败，正在回滚内存更改...")
            _restore_config(config, snapshot)
            logger.info("[API] 批量删除回滚完成")
            all_results = []
            final_failed_servers: list[dict[str, Any]] = []
            for server_request in request.servers:
                final_failed_servers.append({
                    "recName": server_request.recName,
                    "recType": server_request.recType,
                    "error": "保存配置文件失败"
                })
            failed_servers = final_failed_servers
        else:
            logger.info("[API] 批量删除服务器后保存配置文件成功")
            for server_request in request.servers:
                server_key = (server_request.recType.upper(), server_request.recName)
                if server_key in deleted_server_keys and \
                    not any(f["recName"] == server_request.recName and f["recType"] == server_request.recType for f in failed_servers):
                    all_results.append({
                        "recName": server_request.recName,
                        "recType": server_request.recType,
                        "success": True
                    })

    return {
        "success": len(all_results) > 0,
        "total": len(request.servers),
        "succeeded": len(all_results),
        "failed": len(failed_servers),
        "data": all_results,
        "errors": failed_servers if failed_servers else None
    } 
