from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Optional
import logging


from core.dependencies import get_config, get_logger
from core.models import (
    CreateRoomRequest, RoomConfigRequest, BatchCreateRoomRequest, BatchDeleteRoomRequest
)
from core.services.auth import get_current_user
from core.external.helpers import iterate_server_instances
from core.utils import handle_operation_error

router = APIRouter()

# === 辅助函数 ===

def _resolve_rec_type(rec_type: Optional[str], rec_name: Optional[str], config: dict[str, Any]) -> Optional[str]:
    if not rec_name:
        return rec_type

    recheme_config = config.get("RECHEME")
    if isinstance(recheme_config, dict) and rec_name in recheme_config:
        return "recheme"

    blrec_config = config.get("BLREC")
    if isinstance(blrec_config, dict) and rec_name in blrec_config:
        return "blrec"

    return rec_type

def _room_id_for_server(room_id: int, rec_type: str) -> int | str:
    return str(room_id) if rec_type == "blrec" else room_id

async def _run_room_operation(
    *,
    config: dict[str, Any],
    operation,
    operation_name: str,
    rec_type: Optional[str],
    rec_name: Optional[str],
    current_user: Optional[str],
    api_params: Optional[dict[str, Any]] = None
) -> dict[str, list[dict[str, Any]]]:
    results = await iterate_server_instances(
        config=config,
        operation=operation,
        rec_type=rec_type,
        rec_name=rec_name,
        current_user=current_user,
        operation_name=operation_name,
        api_params=api_params
    )
    return {"data": results}

async def _create_single_room(
    request: CreateRoomRequest,
    recType: Optional[str],
    recName: Optional[str],
    current_user: Optional[str],
    config: dict[str, Any],
    logger: logging.Logger
) -> dict[str, list[dict[str, Any]]]:
    """创建单个房间 (使用依赖注入的 config 和 logger)"""
    effective_rec_type = _resolve_rec_type(recType, recName, config)

    async def create_room_operation(api_instance, rec_name, rec_type, api_info, room_id: int, auto_record: bool):
        return await api_instance.create_room(room_id, auto_record)

    return await _run_room_operation(
        config=config,
        operation=create_room_operation,
        operation_name="创建直播间",
        rec_type=effective_rec_type,
        rec_name=recName,
        current_user=current_user,
        api_params={
            "room_id": request.roomId,
            "auto_record": request.autoRecord
        }
    )

async def _delete_single_room(
    roomId: int,
    recType: Optional[str],
    recName: Optional[str],
    current_user: Optional[str],
    config: dict[str, Any],
    logger: logging.Logger
) -> dict[str, list[dict[str, Any]]]:
    """删除单个房间 (使用依赖注入的 config 和 logger)"""
    logger.debug(f"[API] 请求删除房间ID为 {roomId} 的直播间")
    if recName:
        logger.debug(f"[API] 指定录播机实例: {recName}")
    effective_rec_type = _resolve_rec_type(recType, recName, config)

    async def delete_room_operation(api_instance, rec_name, rec_type, api_info, room_id: int):
        result = await api_instance.delete_room(_room_id_for_server(room_id, rec_type))
        if result is None:
            return None
        return {
            "roomid": room_id,
            "recServer": {
                "recName": rec_name,
                "recType": rec_type,
                "recHost": api_instance.host,
                "recManage": api_info.get("MANAGE", True)
            }
        }

    return await _run_room_operation(
        config=config,
        operation=delete_room_operation,
        operation_name="删除直播间",
        rec_type=effective_rec_type,
        rec_name=recName,
        current_user=current_user,
        api_params={"room_id": roomId}
    )

async def _run_recheme_room_operation(
    *,
    roomId: int,
    recType: str,
    recName: Optional[str],
    current_user: str,
    config: dict[str, Any],
    operation,
    operation_name: str,
    unsupported_detail: str,
    api_params: Optional[dict[str, Any]] = None
) -> dict[str, list[dict[str, Any]]]:
    if recType != "recheme":
        raise HTTPException(status_code=400, detail=unsupported_detail)

    params = {"room_id": roomId}
    if api_params:
        params.update(api_params)

    return await _run_room_operation(
        config=config,
        operation=operation,
        operation_name=operation_name,
        rec_type="recheme",
        rec_name=recName,
        current_user=current_user,
        api_params=params
    )

# === API ===

@router.get("/room")
async def get_rooms(
    recType: Optional[str] = None,
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
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
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """创建新的直播间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求创建新的直播间: {request.roomId}")
    
    try:
        logger.debug(f"[API] 请求创建房间ID为 {request.roomId} 的直播间")

        recType = request.recType
        recName = request.recName

        if recName:
            logger.debug(f"[API] 指定录播机实例: {recName}")
        elif recType:
            logger.debug(f"[API] 指定录播机类型: {recType}")

        return await _create_single_room(request, recType, recName, current_user, config, logger)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] 创建房间失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建房间失败: {str(e)}")

@router.post("/room/batch")
async def batch_create_rooms(
    request: BatchCreateRoomRequest,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """批量创建直播间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求批量创建直播间")
    logger.debug(f"[API] 请求批量创建 {len(request.rooms)} 个直播间")
    recType = request.recType
    recName = request.recName
    all_results: list[dict[str, Any]] = []
    
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
    recType: Optional[str] = None,
    recName: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """删除房间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求删除房间 {roomId}, 类型: {recType}, 名称: {recName}")
    return await _delete_single_room(roomId, recType, recName, current_user, config, logger)


@router.delete("/room/batch")
async def batch_delete_rooms(
    request: BatchDeleteRoomRequest,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """批量删除房间 (使用依赖注入的 logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求批量删除房间")
    logger.debug(f"[API] 请求批量删除 {len(request.rooms)} 个直播间")
    
    all_results: list[dict[str, Any]] = []
    failed_rooms: list[dict[str, Any]] = []
    
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
    recType: Optional[str] = None,
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """获取指定房间的数据 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 请求获取房间ID为 {roomId} 的数据, 类型: {recType}")
    if recType and recType not in ["recheme", "blrec"]:
        raise HTTPException(status_code=400, detail="不支持的录播类型")

    async def get_room_operation(api_instance, rec_name, rec_type, api_info, room_id: int):
        return await api_instance.get_room(_room_id_for_server(room_id, rec_type))

    try:
        return await _run_room_operation(
            config=config,
            operation=get_room_operation,
            operation_name="获取直播间",
            rec_type=recType,
            rec_name=None,
            current_user=None,
            api_params={"room_id": roomId}
        )
    except HTTPException:
        if recType == "recheme":
            error_msg = "录播姬不存在该直播间"
        elif recType == "blrec":
            error_msg = "BLREC不存在该直播间"
        else:
            error_msg = "不存在该直播间"
        raise HTTPException(status_code=404, detail=error_msg)


@router.post("/room/{roomId}/config")
async def update_room_config(
    roomId: int,
    request: RoomConfigRequest,
    recType: str = "recheme",
    recName: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """更新房间配置 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求更新房间 {roomId} 的配置")
    logger.debug(f"[API] 请求修改房间ID为 {roomId} 的设置, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")

    async def update_config_operation(api_instance, rec_name, rec_type, api_info, room_id: int, room_config: dict[str, Any]):
        return await api_instance.update_room_config(room_id, room_config)

    return await _run_recheme_room_operation(
        roomId=roomId,
        recType=recType,
        recName=recName,
        current_user=current_user,
        config=config,
        operation=update_config_operation,
        operation_name="修改房间设置",
        unsupported_detail="当前只支持录播姬配置修改",
        api_params={"room_config": request.dict()}
    )


@router.post("/room/{roomId}/start")
async def start_room_recording(
    roomId: int,
    recType: str = "recheme",
    recName: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """开始录制 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求开始录制房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")

    async def start_operation(api_instance, rec_name, rec_type, api_info, room_id: int):
        return await api_instance.start_recording(room_id)

    return await _run_recheme_room_operation(
        roomId=roomId,
        recType=recType,
        recName=recName,
        current_user=current_user,
        config=config,
        operation=start_operation,
        operation_name="开始录制",
        unsupported_detail="当前只支持录播姬录制"
    )

@router.post("/room/{roomId}/stop")
async def stop_room_recording(
    roomId: int,
    recType: str = "recheme",
    recName: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """停止录制 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求停止录制房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")

    async def stop_operation(api_instance, rec_name, rec_type, api_info, room_id: int):
        return await api_instance.stop_recording(room_id)

    return await _run_recheme_room_operation(
        roomId=roomId,
        recType=recType,
        recName=recName,
        current_user=current_user,
        config=config,
        operation=stop_operation,
        operation_name="停止录制",
        unsupported_detail="当前只支持录播姬录制"
    )


@router.post("/room/{roomId}/split")
async def split_room_recording(
    roomId: int,
    recType: str = "recheme",
    recName: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """手动分段 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求手动分段房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")

    async def split_operation(api_instance, rec_name, rec_type, api_info, room_id: int):
        return await api_instance.split_recording(room_id)

    return await _run_recheme_room_operation(
        roomId=roomId,
        recType=recType,
        recName=recName,
        current_user=current_user,
        config=config,
        operation=split_operation,
        operation_name="手动分段",
        unsupported_detail="当前只支持录播姬分段"
    )


@router.post("/room/{roomId}/refresh")
async def refresh_room(
    roomId: int,
    recType: str = "recheme",
    recName: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    config: dict[str, Any] = Depends(get_config),
    logger: logging.Logger = Depends(get_logger)
):
    """刷新房间信息 (使用依赖注入的 config, logger)"""
    logger.debug(f"[API] 用户 {current_user} 请求刷新房间 {roomId}, 类型: {recType}, 名称: {recName}")
    if recName:
        logger.debug(f"[API] 指定录播姬实例: {recName}")

    async def refresh_operation(api_instance, rec_name, rec_type, api_info, room_id: int):
        return await api_instance.refresh_room(room_id)

    return await _run_recheme_room_operation(
        roomId=roomId,
        recType=recType,
        recName=recName,
        current_user=current_user,
        config=config,
        operation=refresh_operation,
        operation_name="刷新房间信息",
        unsupported_detail="当前只支持录播姬刷新"
    )
