import asyncio, aiohttp
from typing import Any

from core.logs import log, log_print

logger = log()

class RechemeAPI:
    """录播姬 API"""
    
    def __init__(self, host: str, name: str, basic_auth: bool = False, username: str = "", password: str = "", manage: bool = True):
        """
        初始化录播姬 API
        :param host: 录播姬服务器地址
        :param name: 录播姬实例名称
        :param basic_auth: 是否启用 Basic 认证
        :param username: Basic 认证用户名
        :param password: Basic 认证密码
        :param manage: 是否允许管理操作
        """
        self.host = host.rstrip('/')
        self.name = name
        self.manage = manage
        self.auth = None
        if basic_auth and username and password:
            self.auth = aiohttp.BasicAuth(login=username, password=password)
            logger.debug(f"[录播姬] {self.name} Basic认证已配置")

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """
        异步发送 HTTP 请求到录播姬 API
        :param endpoint: API 端点
        :param method: HTTP 方法
        :param data: POST/PUT 请求的 JSON 数据
        :param params: GET 请求的 URL 参数
        :return: API 响应数据或 None
        """
        url = f"{self.host}/api/{endpoint}"
        async with aiohttp.ClientSession(auth=self.auth, trust_env=False) as session:
            try:
                async with session.request(
                    method,
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    json=data,
                    params=params
                ) as response:
                    if response.status in [200, 201, 204]:
                        if response.status == 204:
                            return {}
                        response_text = await response.text()
                        if not response_text.strip():
                            return {}
                        try:
                            response_data = await response.json()
                        except aiohttp.ContentTypeError:
                            log_print(f"[录播姬] {self.name} API {url} 响应不是有效的 JSON (状态码 {response.status})", "ERROR")
                            return None
                        except Exception as json_err:
                            log_print(f"[录播姬] {self.name} 解析 API {url} 响应 JSON 失败: {json_err}", "ERROR")
                            return None
                        if isinstance(response_data, dict):
                            return response_data
                        if isinstance(response_data, list) and all(isinstance(item, dict) for item in response_data):
                            return response_data
                        log_print(f"[录播姬] {self.name} API {url} 响应 JSON 类型不符合预期", "ERROR")
                        return None
                    elif response.status == 401:
                        log_print(f"[录播姬] {self.name} API {url} 认证失败 (状态码 {response.status}). 请检查认证配置。", "ERROR")
                        return None
                    else:
                        log_print(f"[录播姬] {self.name} API {url} 请求失败 (状态码 {response.status}): {await response.text()}", "ERROR")
                        return None
            except aiohttp.ClientConnectorError as e:
                log_print(f"[录播姬] {self.name} 连接 API {url} 失败: {e}. 请检查网络连接和录播机地址。", "ERROR")
                return None
            except asyncio.TimeoutError:
                log_print(f"[录播姬] {self.name} 请求 API {url} 超时.", "ERROR")
                return None
            except Exception as e:
                log_print(f"[录播姬] {self.name} 请求 API {url} 时发生未知错误: {e}", "ERROR", exc_info=True)
                return None

    async def get_global_config(self) -> dict | None:
        """获取录播姬全局配置"""
        result = await self._make_request("config/global", method="GET")
        return result if isinstance(result, dict) else None

    async def update_global_config(self, config_data: dict) -> bool:
        """更新录播姬全局配置"""
        response_data = await self._make_request("config/global", method="POST", data=config_data)
        return response_data is not None

    async def get_rooms(self) -> list[dict[str, Any]]:
        """获取所有直播间信息"""
        data = await self._make_request("room")
        if not isinstance(data, list):
            return []
            
        for item in data:
            item["recServer"] = {
                "recName": self.name,
                "recType": "recheme",
                "recHost": self.host,
                "recManage": self.manage
            }
        return data

    async def get_room(self, room_id: int) -> dict[str, Any] | None:
        """
        获取指定直播间信息
        :param room_id: 房间号
        """
        data = await self._make_request(f"room/{room_id}")
        if not isinstance(data, dict):
            return None
            
        data["recServer"] = {
            "recName": self.name,
            "recType": "recheme",
            "recHost": self.host,
            "recManage": self.manage
        }
        return data

    async def get_room_stats(self, room_id: int) -> dict[str, Any] | None:
        """
        获取直播间录制统计信息
        :param room_id: 房间号
        """
        data = await self._make_request(f"room/{room_id}/stats")
        return data if isinstance(data, dict) else None

    async def get_room_iostats(self, room_id: int) -> dict[str, Any] | None:
        """
        获取直播间 IO 统计信息
        :param room_id: 房间号
        """
        data = await self._make_request(f"room/{room_id}/iostats")
        return data if isinstance(data, dict) else None

    async def get_room_config(self, room_id: int) -> dict[str, Any] | None:
        """
        获取直播间设置
        :param room_id: 房间号
        """
        data = await self._make_request(f"room/{room_id}/config")
        return data if isinstance(data, dict) else None

    def _check_manage_permission(self, operation: str) -> bool:
        """检查是否有管理权限"""
        if not self.manage:
            log_print(f"[录播姬] {self.name} 未启用管理功能，禁止{operation}操作", "ERROR")
            return False
        return True

    async def create_room(self, room_id: int, auto_record: bool = True) -> dict[str, Any] | None:
        """
        创建新的直播间
        :param room_id: 房间号
        :param auto_record: 是否启用自动录制
        :return: 创建结果
        """
        if not self._check_manage_permission("创建房间"):
            return None
        data = {
            "roomId": room_id,
            "autoRecord": auto_record
        }
        response = await self._make_request("room", method="POST", data=data)
        if not isinstance(response, dict) or not response:
            return None
        response["recServer"] = {
            "recName": self.name,
            "recType": "recheme",
            "recHost": self.host,
            "recManage": self.manage
        }
        return response 

    async def update_room_config(self, room_id: int, config: dict[str, Any]) -> dict[str, Any] | None:
        """
        修改直播间设置
        :param room_id: 房间号
        :param config: 配置信息
        :return: 更新结果
        """
        if not self._check_manage_permission("修改设置"):
            return None
        data = await self._make_request(f"room/{room_id}/config", method="POST", data=config)
        return data if isinstance(data, dict) and data else None

    async def start_recording(self, room_id: int) -> dict[str, Any] | None:
        """
        开始录制
        :param room_id: 房间号
        :return: 操作结果
        """
        if not self._check_manage_permission("开始录制"):
            return None
        data = await self._make_request(f"room/{room_id}/start", method="POST")
        return data if isinstance(data, dict) and data else None

    async def stop_recording(self, room_id: int) -> dict[str, Any] | None:
        """
        停止录制
        :param room_id: 房间号
        :return: 操作结果
        """
        if not self._check_manage_permission("停止录制"):
            return None
        data = await self._make_request(f"room/{room_id}/stop", method="POST")
        return data if isinstance(data, dict) and data else None

    async def split_recording(self, room_id: int) -> dict[str, Any] | None:
        """
        手动分段
        :param room_id: 房间号
        :return: 操作结果
        """
        if not self._check_manage_permission("手动分段"):
            return None
        data = await self._make_request(f"room/{room_id}/split", method="POST")
        return data if isinstance(data, dict) and data else None

    async def refresh_room(self, room_id: int) -> dict[str, Any] | None:
        """
        刷新直播间信息
        :param room_id: 房间号
        :return: 刷新结果
        """
        if not self._check_manage_permission("刷新房间"):
            return None
        data = await self._make_request(f"room/{room_id}/refresh", method="POST")
        return data if isinstance(data, dict) and data else None

    async def delete_room(self, room_id: int) -> dict[str, Any] | None:
        """
        删除直播间
        :param room_id: 房间号
        :return: 删除结果
        """
        if not self._check_manage_permission("删除房间"):
            return None
        result = await self._make_request(f"room/{room_id}", method="DELETE")
        return result if isinstance(result, dict) else None
