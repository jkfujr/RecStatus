import asyncio, aiohttp, copy, random
from urllib.parse import urljoin
from collections import defaultdict
from typing import Any, TypedDict

from core.logs import log
from core.external.recheme import RechemeAPI
from core.external.factory import create_recheme_instance

logger = log()


class ServerHealth(TypedDict):
    failures: int
    last_failure: float
    backoff_until: float


class EnabledCookieInstance(TypedDict):
    rec_name: str
    api_info: dict[str, Any]
    instance_key: str
    cookie_config: dict[str, Any]


class CurrentCookieData(TypedDict):
    cookie: str
    dedeUserId: str | None


def _new_string_list() -> list[str]:
    return []


def _new_server_health() -> ServerHealth:
    return {"failures": 0, "last_failure": 0.0, "backoff_until": 0.0}


class CookieManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config: dict[str, Any] = config
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.session: aiohttp.ClientSession | None = None
        self.running = False
        self._summary_log_lock = asyncio.Lock()
        self._reset_runtime_state()

    def _reset_runtime_state(self) -> None:
        self.tasks = {}
        self._user_instances: defaultdict[str, list[str]] = defaultdict(_new_string_list)
        self._logged_configs: set[str] = set()
        self._logged_cookies: set[str] = set()
        self._batch_check_logged = False
        self._cookie_results: dict[str, list[str]] = {"updated": [], "unchanged": [], "failed": []}
        self._cookie_success_logged: set[str] = set()
        self._cookie_updates_batch: defaultdict[str, list[str]] = defaultdict(_new_string_list)
        self._cycle_completed_counter = 0
        self._server_health: defaultdict[str, ServerHealth] = defaultdict(_new_server_health)

    async def start(self) -> None:
        if self.running:
            return

        recheme_config = self.config.get("RECHEME")
        if not isinstance(recheme_config, dict):
            logger.warning("[Cookie管理器] 配置中未找到 RECHEME 部分，跳过。")
            return

        self._reset_runtime_state()
        enabled_instances: list[EnabledCookieInstance] = []
        disabled_instances: list[dict[str, str]] = []

        for rec_name, api_info_list in recheme_config.items():
            if not isinstance(api_info_list, list):
                continue

            for i, api_info in enumerate(api_info_list):
                if not isinstance(api_info, dict):
                    continue
                instance_key = f"{rec_name}_{i}"
                cookie_config = self._get_effective_cookie_config(rec_name, api_info)

                if cookie_config and cookie_config.get("ENABLE", False):
                    enabled_instances.append({
                        "rec_name": rec_name,
                        "api_info": api_info,
                        "instance_key": instance_key,
                        "cookie_config": cookie_config
                    })
                else:
                    disabled_instances.append({
                        "rec_name": rec_name,
                        "url": api_info.get("URL", "未知地址")
                    })

        if enabled_instances:
            enabled_names = [instance["rec_name"] for instance in enabled_instances]
            logger.info(f"[Cookie管理器] 为 {len(enabled_names)} 个实例启动 Cookie 管理: {', '.join(enabled_names)}")
        
        if disabled_instances:
            disabled_names = [instance["rec_name"] for instance in disabled_instances]
            logger.debug(f"[Cookie管理器] {len(disabled_instances)} 个实例未启用 Cookie 管理: {', '.join(disabled_names)}")

        if not enabled_instances:
            logger.info("[Cookie管理器] 未找到已启用的 Cookie 管理实例，跳过启动。")
            return

        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        self.running = True
        logger.info("[Cookie管理器] 启动...")

        logger.debug("[Cookie管理器] 预扫描实例 Cookie 信息...")
        for instance in enabled_instances:
            try:
                recheme_api = create_recheme_instance(instance["api_info"], instance["rec_name"], self.config)
                if not hasattr(recheme_api, 'get_global_config'):
                    continue
                
                cookie_data = await self._get_current_recheme_cookie(recheme_api, silent=True)
                if cookie_data and cookie_data.get("dedeUserId"):
                    dede_user_id = cookie_data["dedeUserId"]
                    user_key = f"uid_{dede_user_id}"
                    if instance["rec_name"] not in self._user_instances[user_key]:
                        self._user_instances[user_key].append(instance["rec_name"])
            except Exception as e:
                logger.error(f"[Cookie管理器] 预扫描 {instance['rec_name']} 失败: {e}")
        
        for user_key, instances in self._user_instances.items():
            if user_key.startswith("uid_"):
                dede_user_id = user_key[4:]
                self._log_dede_user_id_details(dede_user_id)

        for instance in enabled_instances:
            recheme_api = create_recheme_instance(instance["api_info"], instance["rec_name"], self.config)
            if not hasattr(recheme_api, 'get_global_config') or not hasattr(recheme_api, 'update_global_config'):
                logger.error(f"[Cookie管理器] RechemeAPI 实例缺少必要方法，无法为 {instance['rec_name']} 管理 Cookie")
                continue

            self.tasks[instance["instance_key"]] = asyncio.create_task(
                self._manage_instance(instance["rec_name"], recheme_api, instance["cookie_config"])
            )

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        logger.info("[Cookie管理器] 停止中...")
        for task in self.tasks.values():
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
        logger.info("[Cookie管理器] 已停止。")
        self.tasks = {}

    async def reload(self, config: dict[str, Any]) -> None:
        """重新加载配置并重启 Cookie 管理任务"""
        if self.running:
            await self.stop()
        self.config = config
        self._reset_runtime_state()
        await self.start()

    def _get_effective_cookie_config(self, rec_name: str, api_info: dict[str, Any]) -> dict[str, Any]:
        """获取生效的 Cookie 配置 (实例覆盖全局)"""
        global_cookie_config = self.config.get("COOKIE", {})
        if not isinstance(global_cookie_config, dict):
            global_cookie_config = {}

        recheme_config = self.config.get("RECHEME", {})
        if not isinstance(recheme_config, dict):
            recheme_config = {}

        recheme_global_cookie_config = recheme_config.get("COOKIE", {})
        if not isinstance(recheme_global_cookie_config, dict):
            recheme_global_cookie_config = {}

        instance_cookie_config = api_info.get("COOKIE", {})
        if not isinstance(instance_cookie_config, dict):
            instance_cookie_config = {}

        effective_enable = instance_cookie_config.get(
            "ENABLE",
            recheme_global_cookie_config.get(
                "ENABLE",
                global_cookie_config.get("ENABLE", False)
            )
        )

        if not effective_enable:
            return {"ENABLE": False}

        # 按优先级使用配置
        cookie_key_to_use = None
        # 查找实例配置中的 key (排除 'ENABLE')
        if isinstance(instance_cookie_config, dict):
            for key in instance_cookie_config:
                if key != 'ENABLE':
                    cookie_key_to_use = key
                    break
        # 查找录播姬全局配置中的 key (排除 'ENABLE')
        if not cookie_key_to_use and isinstance(recheme_global_cookie_config, dict):
            for key in recheme_global_cookie_config:
                if key != 'ENABLE':
                    cookie_key_to_use = key
                    break
        # 查找全局配置中的 key (排除 'ENABLE')
        if not cookie_key_to_use and isinstance(global_cookie_config, dict):
            for key in global_cookie_config:
                if key != 'ENABLE':
                    cookie_key_to_use = key
                    break

        if not cookie_key_to_use:
            logger.warning(f"[Cookie管理器] {rec_name}: 配置已启用，但未找到有效的 Cookie 配置块 (如 C1)。")
            return {"ENABLE": False}


        global_c_conf = global_cookie_config.get(cookie_key_to_use, {})
        recheme_global_c_conf = recheme_global_cookie_config.get(cookie_key_to_use, {})
        instance_c_conf = instance_cookie_config.get(cookie_key_to_use, {})
        
        if not isinstance(global_c_conf, dict):
            global_c_conf = {}
        if not isinstance(recheme_global_c_conf, dict):
            recheme_global_c_conf = {}
        if not isinstance(instance_c_conf, dict):
            instance_c_conf = {}
        
        final_c_conf = global_c_conf.copy()
        final_c_conf.update(recheme_global_c_conf)
        final_c_conf.update(instance_c_conf)
        final_c_conf['ENABLE'] = True
        return final_c_conf

    async def _log_batch_results(self) -> None:
        if self._cookie_results["updated"]:
            names = self._cookie_results["updated"]
            count = len(names)
            logger.info(f"[Cookie管理器] {count}个实例的Cookie已更新: {', '.join(names)}")
            self._cookie_results["updated"] = []
            
        if self._cookie_results["unchanged"]:
            names = self._cookie_results["unchanged"]
            count = len(names)
            logger.debug(f"[Cookie管理器] {count}个实例的Cookie无需更新: {', '.join(names)}")
            self._cookie_results["unchanged"] = []
            
        if self._cookie_results["failed"]:
            names = self._cookie_results["failed"]
            count = len(names)
            logger.warning(f"[Cookie管理器] {count}个实例获取Cookie失败: {', '.join(names)}")
            self._cookie_results["failed"] = []
            
        self._batch_check_logged = False

    async def _manage_instance(self, rec_name: str, recheme_api: RechemeAPI, cookie_config: dict[str, Any]) -> None:
        mode = str(cookie_config.get("MODE", "random"))
        check_interval = int(cookie_config.get("CHECK_INTERVAL", 3600))
        random_interval = int(cookie_config.get("RANDOM_CHANGE_INTERVAL", 86400))
        cookie_server_url_value = cookie_config.get("VALUE")
        cookie_server_url = str(cookie_server_url_value).strip() if cookie_server_url_value else ""
        cookie_server_token_value = cookie_config.get("TOKEN")
        cookie_server_token = str(cookie_server_token_value) if cookie_server_token_value else None
        request_timeout = int(cookie_config.get("REQUEST_TIMEOUT", 10))
        max_retries = int(cookie_config.get("MAX_RETRIES", 3))

        if not cookie_server_url:
            logger.error(f"[Cookie管理器] {rec_name}: 未配置 Cookie 服务器地址，无法管理")
            return

        interval = random_interval if mode == "random" else check_interval
        
        config_key = f"{mode}_{interval}_{cookie_server_url}"
        if config_key not in self._logged_configs:
            logger.info(f"[Cookie管理器] 配置组: 模式={mode}, 更新间隔={interval}s, Cookie服务器={cookie_server_url}")
            self._logged_configs.add(config_key)

        await asyncio.sleep(10)

        while self.running:
            try:
                if len(self.tasks) > 5:
                    if not self._batch_check_logged:
                        logger.debug(f"[Cookie管理器] 正在检查/更新 {len(self.tasks)} 个实例的Cookie")
                        self._batch_check_logged = True
                else:
                    logger.debug(f"[Cookie管理器] {rec_name}: 开始检查/更新 Cookie")
                
                new_cookie: str | None = None
                current_cookie_data: CurrentCookieData | None = None
                current_cookie_str: str | None = None
                current_dede_user_id: str | None = None

                if mode == "onlysync":
                    current_cookie_data = await self._get_current_recheme_cookie(recheme_api)
                    if current_cookie_data:
                        current_dede_user_id = current_cookie_data.get("dedeUserId")
                        if not current_dede_user_id:
                            logger.warning(f"[Cookie管理器] {rec_name}: 无法获取DedeUserID，将随机获取")
                            mode = "random"
                        else:
                            user_key = f"uid_{current_dede_user_id}"
                            if rec_name not in self._user_instances[user_key]:
                                self._user_instances[user_key].append(rec_name)
                            
                            log_key = f"uid_log_{current_dede_user_id}"
                            if log_key not in self._logged_cookies:
                                logger.debug(f"[Cookie管理器] DedeUserID={current_dede_user_id} ({len(self._user_instances[user_key])}个实例)")
                                self._logged_cookies.add(log_key)

                if (mode == "onlysync" and current_dede_user_id) or mode == "random":
                    new_cookie = await self._get_cookie_from_server(
                        cookie_server_url,
                        cookie_server_token,
                        mode,
                        current_dede_user_id,
                        request_timeout,
                        max_retries
                    )

                if new_cookie:
                    if mode == "random":
                        current_cookie_data_compare = await self._get_current_recheme_cookie(recheme_api)
                        if current_cookie_data_compare:
                            current_cookie_str = current_cookie_data_compare.get("cookie")
                    elif current_cookie_data:
                        current_cookie_str = current_cookie_data.get("cookie")

                    if current_cookie_str is None or new_cookie != current_cookie_str:
                        success = await self._update_recheme_cookie(recheme_api, new_cookie)
                        if success:
                            uid_key = "random" if mode == "random" else current_dede_user_id or "unknown"
                            self._cookie_updates_batch[uid_key].append(rec_name)
                            
                        if rec_name not in self._cookie_results["updated"]:
                            self._cookie_results["updated"].append(rec_name)
                    else:
                        if rec_name not in self._cookie_results["unchanged"]:
                            self._cookie_results["unchanged"].append(rec_name)
                else:
                    if rec_name not in self._cookie_results["failed"]:
                        self._cookie_results["failed"].append(rec_name)

                expected_tasks = len(self.tasks)
                completed_in_batch = len(self._cookie_results["updated"]) + len(self._cookie_results["unchanged"]) + len(self._cookie_results["failed"])

                async with self._summary_log_lock:
                    completed_in_batch = len(self._cookie_results["updated"]) + len(self._cookie_results["unchanged"]) + len(self._cookie_results["failed"])
                    has_results_to_log = self._cookie_results["updated"] or self._cookie_results["unchanged"] or self._cookie_results["failed"]
                    
                    if completed_in_batch >= expected_tasks and has_results_to_log:
                        logger.debug(f"[Cookie管理器] {rec_name}: 触发批量日志记录 ({completed_in_batch}/{expected_tasks} 结果已收集)。")
                        await self._log_batch_results()
                        if self._cookie_updates_batch:
                            for uid, instances in self._cookie_updates_batch.items():
                                if len(instances) == 1:
                                    logger.info(f"[Cookie管理器] {instances[0]}: Cookie 更新成功")
                                else:
                                    uid_display = f"DedeUserID={uid}" if uid != "random" else "随机模式"
                                    logger.info(f"[Cookie管理器] {uid_display} 的 {len(instances)} 个实例 Cookie 更新成功: {', '.join(instances)}")
                            self._cookie_updates_batch.clear()
                            
                    self._cycle_completed_counter += 1
                    if self._cycle_completed_counter >= expected_tasks:
                        logger.info(f"[Cookie管理器] 所有 {expected_tasks} 个实例本轮检查处理完成，等待 {interval} 秒 ({interval//3600}小时)...")
                        self._cycle_completed_counter = 0

            except asyncio.CancelledError:
                logger.info(f"[Cookie管理器] {rec_name}: 任务被取消")
                break
            except Exception as e:
                logger.error(f"[Cookie管理器] {rec_name}: 任务出错: {e}", exc_info=True)
                await asyncio.sleep(min(interval // 10, 600))
                continue
            
            await asyncio.sleep(interval)

    async def _get_cookie_from_server(
        self,
        server_url: str,
        token: str | None,
        mode: str,
        dede_user_id: str | None = None,
        timeout: int = 10,
        max_retries: int = 3
    ) -> str | None:
        """
        从 Cookie 服务器 v2 API 获取 Cookie，支持超时重试。
        """
        session = self.session
        if not session or session.closed:
            logger.error("[Cookie管理器] HTTP 会话未启动，无法请求 Cookie 服务器")
            return None

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        v2_params: dict[str, str] = {}
        if mode == "random":
            v2_url = urljoin(server_url, "/api/v1/cookies/random")
            v2_params["format"] = "simple"
        elif mode == "onlysync" and dede_user_id:
            v2_url = urljoin(server_url, f"/api/v1/cookies/{dede_user_id}")
        else:
            logger.error("[Cookie管理器] 无效的模式或缺少 DedeUserID")
            return None

        health_key = f"{server_url}_{mode}"
        server_health = self._server_health[health_key]
        current_time = asyncio.get_event_loop().time()

        if server_health["backoff_until"] > current_time:
            backoff_remaining = round(server_health["backoff_until"] - current_time)
            logger.debug(f"[Cookie管理器] Cookie服务器 {server_url} 暂时不可用，{backoff_remaining}秒后重试")
            return None

        request_timeout = aiohttp.ClientTimeout(total=timeout)

        for retry in range(max_retries):
            if retry > 0:
                backoff_time = min(2 ** retry + random.uniform(0, 1), 60)
                logger.warning(f"[Cookie管理器] 请求Cookie服务器超时/错误，第{retry}次重试，等待{backoff_time:.2f}秒...")
                await asyncio.sleep(backoff_time)

            try:
                async with session.get(v2_url, headers=headers, params=v2_params, timeout=request_timeout) as response:
                    if response.status != 200:
                        logger.warning(f"[Cookie管理器] v2 API 请求失败: {response.status}")
                        response.raise_for_status()

                    data = await response.json()
                    if not isinstance(data, dict):
                        logger.warning(f"[Cookie管理器] v2 API 响应不是对象: {data}")
                        self._update_server_health(health_key)
                        return None

                    if mode == "random":
                        cookie_value = data.get("header_string")
                    else:
                        managed = data.get("managed")
                        if not isinstance(managed, dict):
                            logger.warning(f"[Cookie管理器] v2 API 响应缺少 managed 对象: {data}")
                            self._update_server_health(health_key)
                            return None
                        cookie_value = managed.get("header_string")

                    if isinstance(cookie_value, str) and cookie_value:
                        self._reset_server_health(health_key)
                        return cookie_value

                    logger.warning(f"[Cookie管理器] v2 API 响应缺少 header_string: {data}")
                    self._update_server_health(health_key)
                    return None

            except asyncio.TimeoutError:
                logger.warning(f"[Cookie管理器] 请求Cookie服务器超时 (尝试 {retry+1}/{max_retries})")
                if retry == max_retries - 1:
                    self._update_server_health(health_key)
                continue
            
            except aiohttp.ClientResponseError as e:
                logger.error(f"[Cookie管理器] Cookie服务器返回错误状态码: {e.status} {e.message}")
                self._update_server_health(health_key)
                break
            
            except aiohttp.ClientError as e:
                logger.error(f"[Cookie管理器] 连接Cookie服务器失败: {e}")
                self._update_server_health(health_key)
                break
            except Exception as e:
                logger.error(f"[Cookie管理器] 处理响应失败: {e}", exc_info=True)
                self._update_server_health(health_key)
                return None

        logger.error(f"[Cookie管理器] 请求Cookie服务器失败，已重试{max_retries}次")
        return None

    def _reset_server_health(self, health_key: str) -> None:
        server_health = self._server_health[health_key]
        server_health["failures"] = 0
        server_health["backoff_until"] = 0.0

    def _update_server_health(self, health_key: str) -> None:
        """更新服务器健康状态"""
        health = self._server_health[health_key]
        health["failures"] += 1
        health["last_failure"] = asyncio.get_event_loop().time()
        
        # 根据连续失败次数实现指数退避
        if health["failures"] > 1:
            # 计算退避时间：基础时间 * (2^(失败次数-1))，最大不超过30分钟
            backoff_seconds = min(30 * (2 ** (health["failures"] - 1)), 1800)
            health["backoff_until"] = health["last_failure"] + backoff_seconds
            logger.warning(f"[Cookie管理器] Cookie服务器连续{health['failures']}次失败，将在{backoff_seconds}秒后重试")

    async def _get_current_recheme_cookie(self, recheme_api: RechemeAPI, silent: bool = False) -> CurrentCookieData | None:
        """获取录播姬当前的 Cookie 和 DedeUserID"""
        try:
            config_data = await recheme_api.get_global_config()

            if isinstance(config_data, dict):
                optional_cookie = config_data.get("optionalCookie")
                if isinstance(optional_cookie, dict):
                    cookie_value = optional_cookie.get("value")
                    cookie_str = str(cookie_value) if cookie_value else ""
                    if not cookie_str:
                        return None

                    parts = cookie_str.split(';')
                    dede_user_id: str | None = None
                    for part in parts:
                        if part.strip().startswith("DedeUserID="):
                            key_value = part.strip().split('=', 1)
                            if len(key_value) == 2 and not key_value[0].endswith("__ckMd5"):
                                dede_user_id = key_value[1]
                                break
                    
                    if dede_user_id:
                        user_key = f"uid_{dede_user_id}"
                        if recheme_api.name not in self._user_instances[user_key]:
                            self._user_instances[user_key].append(recheme_api.name)
                            
                        log_key = f"uid_log_{dede_user_id}"
                        if not silent and log_key not in self._logged_cookies:
                            self._log_dede_user_id_details(dede_user_id)
                            self._logged_cookies.add(log_key)
                    
                    return {"cookie": cookie_str, "dedeUserId": dede_user_id}
            return None
        except Exception as e:
            if not silent:
                logger.error(f"[Cookie管理器] 获取录播姬 {recheme_api.name} 当前 Cookie 失败: {e}", exc_info=True)
            return None

    def _log_dede_user_id_details(self, dede_user_id: str) -> None:
        """记录 DedeUserID 及其关联实例的详细信息"""
        user_key = f"uid_{dede_user_id}"
        if user_key in self._user_instances:
            instances = self._user_instances[user_key]
            instances_count = len(instances)
            logger.debug(f"[Cookie管理器] DedeUserID={dede_user_id} ({instances_count}个实例): {', '.join(instances)}")
        else:
            logger.warning(f"[Cookie管理器] 尝试记录 DedeUserID={dede_user_id} 的详细信息，但未在实例列表中找到。")

    async def _update_recheme_cookie(self, recheme_api: RechemeAPI, new_cookie: str) -> bool:
        """更新录播姬的 Cookie"""
        try:
            # 获取配置
            current_config = await recheme_api.get_global_config()
            if not current_config:
                logger.error(f"[Cookie管理器] {recheme_api.name}: 无法获取当前配置，无法更新 Cookie。")
                return False

            # 请求体
            update_payload = copy.deepcopy(current_config)
            if "optionalCookie" not in update_payload:
                update_payload["optionalCookie"] = {}

            update_payload["optionalCookie"]["value"] = new_cookie
            update_payload["optionalCookie"]["hasValue"] = True
            
            # 更新请求
            success = await recheme_api.update_global_config(update_payload)

            return success

        except Exception as e:
            logger.error(f"[Cookie管理器] {recheme_api.name}: 更新 Cookie 时出错: {e}", exc_info=True)
            return False
