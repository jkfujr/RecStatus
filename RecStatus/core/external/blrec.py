import asyncio, aiohttp
from typing import Any

from core.logs import log, log_print

logger = log()

class BLRECAPI:
    """BLREC API"""
    
    def __init__(self, host: str, name: str, api_key: str = "", manage: bool = True):
        """
        初始化 BLREC API
        :param host: BLREC 服务器地址
        :param name: BLREC 实例名称
        :param api_key: API 密钥
        :param manage: 是否启用管理功能
        """
        self.host = host.rstrip('/')
        self.name = name
        self.manage = manage
        self.headers: dict[str, str] = {}
        
        if api_key:
            self.headers["x-api-key"] = api_key
            logger.debug(f"[BLREC] {self.name} API密钥已配置")
        
        manage_status = "启用" if self.manage else "禁用"
        logger.debug(f"[BLREC] {self.name} 管理功能{manage_status}")

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """
        异步发送 HTTP 请求到 BLREC API
        :param endpoint: API 端点
        :param method: HTTP 方法
        :param params: 查询参数
        :param json: POST/PUT 请求的 JSON 数据
        :return: API 响应数据或 None
        """
        if not self.manage and method != "GET":
            log_print(f"[BLREC] {self.name} 管理功能已禁用，拒绝 {method} 请求: {endpoint}", "WARNING")
            return None
            
        url = f"{self.host}/api/v1/{endpoint}"
        async with aiohttp.ClientSession(trust_env=False) as session:
            try:
                async with session.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    params=params,
                    json=json
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
                            log_print(f"[BLREC] {self.name} API {url} 响应不是有效的 JSON (状态码 {response.status})", "ERROR")
                            return None
                        except Exception as json_err:
                            log_print(f"[BLREC] {self.name} 解析 API {url} 响应 JSON 失败: {json_err}", "ERROR")
                            return None
                        if isinstance(response_data, dict):
                            return response_data
                        if isinstance(response_data, list) and all(isinstance(item, dict) for item in response_data):
                            return response_data
                        log_print(f"[BLREC] {self.name} API {url} 响应 JSON 类型不符合预期", "ERROR")
                        return None
                    else:
                        error_text = await response.text()
                        try:
                            error_json = await response.json(content_type=None)
                            detail = error_json.get("detail", error_text) if isinstance(error_json, dict) else error_text
                        except Exception:
                            detail = error_text
                        log_print(f"[BLREC] {self.name} 请求失败 (状态码 {response.status}): {detail}, URL: {url}", "ERROR")
                        return None
            except aiohttp.ClientConnectorError as e:
                log_print(f"[BLREC] {self.name} 连接 API {url} 失败: {e}. 请检查网络连接和 BLREC 地址。", "ERROR")
                return None
            except asyncio.TimeoutError:
                log_print(f"[BLREC] {self.name} 请求 API {url} 超时.", "ERROR")
                return None
            except Exception as e:
                log_print(f"[BLREC] {self.name} 请求 API {url} 时发生未知错误: {e}", "ERROR", exc_info=True)
                return None

    async def get_rooms(self, page: int = 1, size: int = 100, select: str = "all") -> list[dict[str, Any]]:
        """获取所有直播间信息"""
        params = {
            "page": page,
            "size": min(max(size, 10), 100),
            "select": select
        }
        
        data = await self._make_request("tasks/data", params=params)
        if not isinstance(data, list):
            return []
            
        for item in data:
            item["recServer"] = {
                "recName": self.name,
                "recType": "blrec",
                "recHost": self.host,
                "recManage": self.manage
            }
        return data

    async def get_room(self, room_id: str) -> dict[str, Any] | None:
        """
        获取指定直播间信息
        :param room_id: 房间号
        :return: 直播间信息
        """
        data = await self._make_request(f"tasks/{room_id}/data")
        if not isinstance(data, dict):
            return None
        
        data["recServer"] = {
            "recName": self.name,
            "recType": "blrec", 
            "recHost": self.host,
            "recManage": self.manage
        }
        return data

    async def get_room_stats(self, room_id: str) -> dict[str, Any] | None:
        """
        获取直播间状态信息
        :param room_id: 房间号
        :return: 状态信息
        """
        data = await self._make_request(f"tasks/{room_id}/stats")
        return data if isinstance(data, dict) else None

    async def get_room_status(self, room_id: str) -> dict[str, Any] | None:
        """
        获取直播间运行状态
        :param room_id: 房间号
        :return: 运行状态
        """
        data = await self._make_request(f"tasks/{room_id}/status")
        return data if isinstance(data, dict) else None

    async def get_room_config(self, room_id: str) -> dict[str, Any] | None:
        """
        获取直播间配置
        :param room_id: 房间号
        :return: 配置信息
        """
        data = await self._make_request(f"tasks/{room_id}/config")
        return data if isinstance(data, dict) and data else None

    async def update_room_config(self, room_id: str, config: dict[str, Any]) -> dict[str, Any] | None:
        """
        更新直播间配置
        :param room_id: 房间号
        :param config: 配置信息
        :return: 更新结果
        """
        data = await self._make_request(f"tasks/{room_id}/config", method="PUT", json=config)
        return data if isinstance(data, dict) and data else None

    async def start_recording(self, room_id: str) -> dict[str, Any] | None:
        """
        开始录制
        :param room_id: 房间号
        :return: 操作结果
        """
        data = await self._make_request(f"tasks/{room_id}/start", method="POST")
        return data if isinstance(data, dict) and data else None

    async def stop_recording(self, room_id: str) -> dict[str, Any] | None:
        """
        停止录制
        :param room_id: 房间号
        :return: 操作结果
        """
        data = await self._make_request(f"tasks/{room_id}/stop", method="POST")
        return data if isinstance(data, dict) and data else None

    async def delete_room(self, room_id: str) -> dict[str, Any] | None:
        """
        删除直播间
        :param room_id: 房间号
        :return: 删除结果 (BLREC DELETE 可能不返回 body, 成功时 _make_request 返回 None 或特定对象)
        """
        result = await self._make_request(f"tasks/{room_id}", method="DELETE")
        return result if isinstance(result, dict) else None

    async def create_room(self, room_id: int, auto_record: bool = True) -> dict[str, Any] | None:
        """创建新的直播间 (注意：BLREC API 可能只接受 room_id)"""
        data = await self._make_request(f"tasks/{room_id}", method="POST")
        if not isinstance(data, dict) or not data:
            data = await self.get_room(str(room_id))
            if not isinstance(data, dict):
                return None

        data["recServer"] = {
            "recName": self.name,
            "recType": "blrec",
            "recHost": self.host,
            "recManage": self.manage
        }
        return data
