from fastapi import APIRouter, Depends, HTTPException
from typing import Dict


from core.dependencies import get_config, get_logger
from core.models import (
    CreateRoomRequest, RoomConfigRequest, BatchCreateRoomRequest, BatchDeleteRoomRequest
)
from core.services.auth import get_current_user
from core.external.factory import create_recheme_instance, create_blrec_instance
from core.external.helpers import iterate_server_instances
from core.utils import get_server_display_host, handle_operation_error

router = APIRouter()

# === 辅助函数 ===

async def _create_single_room(
    request: CreateRoomRequest, 
    recType: str = None, 
    recName: str = None, 
    current_user: str = None,
    config: Dict = None,
    logger = None
):
    """创建单个房间 (使用依赖注入的 config 和 logger)"""
    success_results = []
    
    if recName:
        if "RECHEME" in config and any(recName == name for name in config["RECHEME"]):
            recType = "recheme"
        elif "BLREC" in config and any(recName == name for name in config["BLREC"]):
            recType = "blrec"
    
    if (not recType or recType == "recheme") and "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue
            
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.create_room(request.roomId, request.autoRecord)
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)
    
    if (not recType or recType == "blrec") and "BLREC" in config:
        for rec_name, api_info_list in config["BLREC"].items():
            if recName and rec_name != recName:
                continue
                
            if isinstance(api_info_list, list) and rec_name not in ["BLREC_BASIC", "BLREC_BASIC_KEY"]:
                for api_info in api_info_list:
                    blrec = create_blrec_instance(api_info, rec_name, config)
                    result = await blrec.create_room(request.roomId)
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "blrec", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)
    
    if not success_results:
        error_msg = handle_operation_error("创建直播间", recType or "所有", recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results}

async def _delete_single_room(
    roomId: int, 
    recType: str = None, 
    recName: str = None, 
    current_user: str = None,
    config: Dict = None,
    logger = None
):
    """删除单个房间 (使用依赖注入的 config 和 logger)"""
    logger.debug(f"[API] 请求删除房间ID为 {roomId} 的直播间")
    if recName:
        logger.debug(f"[API] 指定录播机实例: {recName}")
    
    success_results = []
    
    if recName:
        if "RECHEME" in config and any(recName == name for name in config["RECHEME"]):
            recType = "recheme"
        elif "BLREC" in config and any(recName == name for name in config["BLREC"]):
            recType = "blrec"
    
    if (not recType or recType == "recheme") and "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue
            
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.delete_room(roomId)
                    if result is not None:
                        display_host = get_server_display_host(api_info, "recheme", config)
                        success_results.append({
                            "roomid": roomId,
                            "recServer": {
                                "recName": rec_name,
                                "recType": "recheme",
                                "recHost": display_host,
                                "recManage": api_info.get("MANAGE", True)
                            }
                        })
    
    if (not recType or recType == "blrec") and "BLREC" in config:
        for rec_name, api_info_list in config["BLREC"].items():
            if recName and rec_name != recName:
                continue
            
            if isinstance(api_info_list, list) and rec_name not in ["BLREC_BASIC", "BLREC_BASIC_KEY"]:
                for api_info in api_info_list:
                    blrec = create_blrec_instance(api_info, rec_name, config)
                    result = await blrec.delete_room(str(roomId))
                    if result is not None:
                        display_host = get_server_display_host(api_info, "blrec", config)
                        success_results.append({
                            "roomid": roomId,
                            "recServer": {
                                "recName": rec_name,
                                "recType": "blrec",
                                "recHost": display_host,
                                "recManage": api_info.get("MANAGE", True)
                            }
                        })
    
    if not success_results:
        error_msg = handle_operation_error("删除直播间", recType or "所有", recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results}

# === API ===

@router.get("/room")
async def get_rooms(
    recType: str = None,
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """API_获取所有直播间信息 (使用依赖注入的 config 和 logger)"""
    if recType:
        logger.debug(f"[API] 指定录播类型: {recType}")
        
    async def get_rooms_operation(api_instance, rec_name, rec_type, api_info):
        """执行获取房间列表的操作"""
        rooms = await api_instance.get_rooms()
        if rooms is None:
            logger.warning(f"[API] 无法从 {rec_type} {rec_name} 获取房间列表")
            return None
        return rooms

    try:
        rooms = await iterate_server_instances(
            config=config,
            operation=get_rooms_operation,
            rec_type=recType,
            operation_name="获取房间列表"
        )
        return rooms
    except HTTPException as e:
        logger.warning(f"[API] 获取房间列表: {e.detail}")
        return []
    except Exception as e:
        logger.error(f"[API] 获取房间列表失败: {e}", exc_info=True)
        return []


@router.post("/room")
async def create_room(
    request: CreateRoomRequest,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """创建新的直播间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求创建新的直播间: {request.roomId}")
    
    try:
        if request is None or request.roomId is None:
            raise HTTPException(status_code=422, detail="缺少必要参数：roomId")
        
        logger.debug(f"[API] 请求创建房间ID为 {request.roomId} 的直播间")
        
        recType = request.recType if hasattr(request, 'recType') else None
        recName = request.recName if hasattr(request, 'recName') else None
        
        if recName:
            logger.debug(f"[API] 指定录播机实例: {recName}")
        elif recType:
            logger.debug(f"[API] 指定录播机类型: {recType}")
            
        return await _create_single_room(request, recType, recName, current_user, config, logger)
    
    except Exception as e:
        logger.error(f"[API] 创建房间失败: {e}")
        if not isinstance(e, HTTPException):
           raise HTTPException(status_code=500, detail=f"创建房间失败: {str(e)}")
        else:
           raise e

@router.post("/room/batch")
async def batch_create_rooms(
    request: BatchCreateRoomRequest,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """批量创建直播间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求批量创建直播间")
    logger.debug(f"[API] 请求批量创建 {len(request.rooms)} 个直播间")
    recType = request.recType
    recName = request.recName
    all_results = []
    
    for room_request in request.rooms:
        try:
            result = await _create_single_room(room_request, recType, recName, current_user, config, logger)
            if result:
                all_results.extend(result.get("data", []))
        except HTTPException as e:
            logger.error(f"[API] 创建房间 {room_request.roomId} 失败: {e.detail}")
            continue
    
    if not all_results:
        error_msg = handle_operation_error("批量创建直播间", recType or "所有", recName, current_user)
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": all_results}


@router.delete("/room/{roomId}")
async def delete_room(
    roomId: int,
    recType: str = None,
    recName: str = None,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """删除房间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求删除房间 {roomId}, 类型: {recType}, 名称: {recName}")
    return await _delete_single_room(roomId, recType, recName, current_user, config, logger)


@router.delete("/room/batch")
async def batch_delete_rooms(
    request: BatchDeleteRoomRequest,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """批量删除房间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求批量删除房间")
    logger.debug(f"[API] 请求批量删除 {len(request.rooms)} 个直播间")
    
    all_results = []
    failed_rooms = []
    
    for room_request in request.rooms:
        try:
            result = await _delete_single_room(
                room_request.roomId,
                room_request.recType,
                room_request.recName,
                current_user,
                config,
                logger
            )
            if result and "data" in result:
                all_results.extend(result["data"]) 
        except HTTPException as e:
            failed_rooms.append({
                "roomId": room_request.roomId,
                "recType": room_request.recType,
                "recName": room_request.recName,
                "error": e.detail
            })
            logger.error(f"[API] 删除房间 {room_request.roomId} 失败: {e.detail}")
            continue
    
    return {
        "success": len(all_results) > 0 or len(failed_rooms) < len(request.rooms),
        "total": len(request.rooms),
        "succeeded": len(all_results),
        "failed": len(failed_rooms),
        "data": all_results,
        "errors": failed_rooms if failed_rooms else None
    }


@router.get("/room/{roomId:int}")
async def get_room_by_id(
    roomId: int, 
    recType: str = None,
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """获取指定房间的数据 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 请求获取房间ID为 {roomId} 的数据, 类型: {recType}")
    if recType and recType not in ["recheme", "blrec"]:
        raise HTTPException(status_code=400, detail="不支持的录播类型")

    room_data = []
    
    if recType in [None, "recheme"] and "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    data = await recheme.get_room(roomId)
                    if data:
                        if "recServer" in data:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            data["recServer"]["recHost"] = display_host
                        room_data.append(data)
    
    if recType in [None, "blrec"] and "BLREC" in config:
        for rec_name, api_info_list in config["BLREC"].items():
            if isinstance(api_info_list, list) and rec_name not in ["BLREC_BASIC", "BLREC_BASIC_KEY"]:
                for api_info in api_info_list:
                    blrec = create_blrec_instance(api_info, rec_name, config)
                    # data = blrec.get_room(str(roomId)) # 原实现似乎笔误，应为 await
                    data = await blrec.get_room(str(roomId)) 
                    if data:
                        if "recServer" in data:
                            display_host = get_server_display_host(api_info, "blrec", config)
                            data["recServer"]["recHost"] = display_host
                        room_data.append(data)

    if not room_data:
        error_msg = {
            "recheme": "录播姬不存在该直播间",
            "blrec": "BLREC不存在该直播间"
        }.get(recType, "不存在该直播间")
        raise HTTPException(status_code=404, detail=error_msg)
    
    # 返回找到的所有匹配房间实例
    return {"data": room_data}


@router.post("/room/{roomId}/config")
async def update_room_config(
    roomId: int,
    request: RoomConfigRequest,
    recType: str = "recheme",
    recName: str = None,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """更新房间配置 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求更新房间 {roomId} 的配置")
    logger.debug(f"[API] 请求修改房间ID为 {roomId} 的设置, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")
    
    if recType != "recheme":
        raise HTTPException(status_code=400, detail="当前只支持录播姬配置修改")
    
    success_results = []
    if "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue
                
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.update_room_config(roomId, request.dict())
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)
    
    if not success_results:
        error_msg = handle_operation_error("修改房间设置", recType, recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results}


@router.post("/room/{roomId}/start")
async def start_room_recording(
    roomId: int,
    recType: str = "recheme",
    recName: str = None,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """开始录制 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求开始录制房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")
    
    if recType != "recheme":
        raise HTTPException(status_code=400, detail="当前只支持录播姬录制")
    
    success_results = []
    if "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue

            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.start_recording(roomId)
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)

    if not success_results:
        error_msg = handle_operation_error("开始录制", recType, recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results}

@router.post("/room/{roomId}/stop")
async def stop_room_recording(
    roomId: int,
    recType: str = "recheme",
    recName: str = None,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """停止录制 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求停止录制房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")
    
    if recType != "recheme":
        raise HTTPException(status_code=400, detail="当前只支持录播姬录制")
    
    success_results = []
    if "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue
                
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.stop_recording(roomId)
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)
    
    if not success_results:
        error_msg = handle_operation_error("停止录制", recType, recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results}


@router.post("/room/{roomId}/split")
async def split_room_recording(
    roomId: int,
    recType: str = "recheme",
    recName: str = None,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """手动分段 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求手动分段房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")
    
    if recType != "recheme":
        raise HTTPException(status_code=400, detail="当前只支持录播姬分段")
    
    success_results = []
    if "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue
                
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.split_recording(roomId)
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)
    
    if not success_results:
        error_msg = handle_operation_error("手动分段", recType, recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results}


@router.post("/room/{roomId}/refresh")
async def refresh_room(
    roomId: int,
    recType: str = "recheme",
    recName: str = None,
    current_user: str = Depends(get_current_user),
    config: Dict = Depends(get_config),
    logger = Depends(get_logger)
):
    """刷新房间信息 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求刷新房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")
    
    if recType != "recheme":
        raise HTTPException(status_code=400, detail="当前只支持录播姬刷新")
    
    success_results = []
    if "RECHEME" in config:
        for rec_name, api_info_list in config["RECHEME"].items():
            if recName and rec_name != recName:
                continue
                
            if isinstance(api_info_list, list):
                for api_info in api_info_list:
                    recheme = create_recheme_instance(api_info, rec_name, config)
                    result = await recheme.refresh_room(roomId)
                    if result:
                        if "recServer" in result:
                            display_host = get_server_display_host(api_info, "recheme", config)
                            result["recServer"]["recHost"] = display_host
                        success_results.append(result)
    
    if not success_results:
        error_msg = handle_operation_error("刷新房间信息", recType, recName, current_user)
        logger.error(f"[API] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    return {"data": success_results} 