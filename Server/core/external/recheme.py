import asyncio, aiohttp
from typing import Dict, List, Optional, Union

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

    async def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None, params: Dict = None) -> Optional[Union[Dict, List]]:
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
                request_kwargs = {"timeout": aiohttp.ClientTimeout(total=10)}
                if data:
                    request_kwargs["json"] = data
                if params:
                    request_kwargs["params"] = params

                async with session.request(method, url, **request_kwargs) as response:
                    if response.status in [200, 201]:
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            log_print(f"[录播姬] {self.name} API {url} 响应不是有效的 JSON (状态码 {response.status})", "ERROR")
                            return None
                        except Exception as json_err:
                             log_print(f"[录播姬] {self.name} 解析 API {url} 响应 JSON 失败: {json_err}", "ERROR")
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
        return result

    async def update_global_config(self, config_data: dict) -> bool:
        """更新录播姬全局配置"""
        response_data = await self._make_request("config/global", method="POST", data=config_data)
        return response_data is not None

    async def get_rooms(self) -> List[Dict]:
        """获取所有直播间信息"""
        data = await self._make_request("room")
        if not data:
            return []
            
        for item in data:
            item["recServer"] = {
                "recName": self.name,
                "recType": "recheme",
                "recHost": self.host,
                "recManage": self.manage
            }
        return data

    async def get_room(self, room_id: int) -> Optional[Dict]:
        """
        获取指定直播间信息
        :param room_id: 房间号
        """
        data = await self._make_request(f"room/{room_id}")
        if not data:
            return None
            
        data["recServer"] = {
            "recName": self.name,
            "recType": "recheme",
            "recHost": self.host,
            "recManage": self.manage
        }
        return data

    async def get_room_stats(self, room_id: int) -> Optional[Dict]:
        """
        获取直播间录制统计信息
        :param room_id: 房间号
        """
        return await self._make_request(f"room/{room_id}/stats")

    async def get_room_iostats(self, room_id: int) -> Optional[Dict]:
        """
        获取直播间 IO 统计信息
        :param room_id: 房间号
        """
        return await self._make_request(f"room/{room_id}/iostats")

    async def get_room_config(self, room_id: int) -> Optional[Dict]:
        """
        获取直播间设置
        :param room_id: 房间号
        """
        return await self._make_request(f"room/{room_id}/config")

    def _check_manage_permission(self, operation: str) -> bool:
        """检查是否有管理权限"""
        if not self.manage:
            log_print(f"[录播姬] {self.name} 未启用管理功能，禁止{operation}操作", "ERROR")
            return False
        return True

    async def create_room(self, room_id: int, auto_record: bool = True) -> Optional[Dict]:
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
        if response:
            response["recServer"] = {
                "recName": self.name,
                "recType": "recheme",
                "recHost": self.host,
                "recManage": self.manage
            }
        return response 

    async def update_room_config(self, room_id: int, config: Dict) -> Optional[Dict]:
        """
        修改直播间设置
        :param room_id: 房间号
        :param config: 配置信息
        :return: 更新结果
        """
        if not self._check_manage_permission("修改设置"):
            return None
        return await self._make_request(f"room/{room_id}/config", method="POST", json=config)

    async def start_recording(self, room_id: int) -> Optional[Dict]:
        """
        开始录制
        :param room_id: 房间号
        :return: 操作结果
        """
        if not self._check_manage_permission("开始录制"):
            return None
        return await self._make_request(f"room/{room_id}/start", method="POST")

    async def stop_recording(self, room_id: int) -> Optional[Dict]:
        """
        停止录制
        :param room_id: 房间号
        :return: 操作结果
        """
        if not self._check_manage_permission("停止录制"):
            return None
        return await self._make_request(f"room/{room_id}/stop", method="POST")

    async def split_recording(self, room_id: int) -> Optional[Dict]:
        """
        手动分段
        :param room_id: 房间号
        :return: 操作结果
        """
        if not self._check_manage_permission("手动分段"):
            return None
        return await self._make_request(f"room/{room_id}/split", method="POST")

    async def refresh_room(self, room_id: int) -> Optional[Dict]:
        """
        刷新直播间信息
        :param room_id: 房间号
        :return: 刷新结果
        """
        if not self._check_manage_permission("刷新房间"):
            return None
        return await self._make_request(f"room/{room_id}/refresh", method="POST")

    async def delete_room(self, room_id: int) -> Optional[Dict]:
        """
        删除直播间
        :param room_id: 房间号
        :return: 删除结果
        """
        if not self._check_manage_permission("删除房间"):
            return None
        result = await self._make_request(f"room/{room_id}", method="DELETE")
        return result 