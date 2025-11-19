import asyncio, aiohttp, copy, random
from urllib.parse import urljoin
from collections import defaultdict

from core.logs import log
from core.external.recheme import RechemeAPI
from core.external.factory import create_recheme_instance

logger = log()

class CookieManager:
    def __init__(self, config):
        self.config = config
        self.tasks = {}
        self.session = None
        self.running = False
        self._user_instances = defaultdict(list)
        self._logged_configs = set()
        self._logged_cookies = set()
        self._batch_check_logged = False
        self._cookie_results = {"updated": [], "unchanged": [], "failed": []}
        self._cookie_success_logged = set()
        self._cookie_updates_batch = defaultdict(list)
        self._summary_log_lock = asyncio.Lock()
        self._cycle_completed_counter = 0
        self._server_health = defaultdict(lambda: {"failures": 0, "last_failure": 0, "backoff_until": 0})

    async def start(self):
        if self.running:
            return
        self.running = True
        # 配置aiohttp会话参数以优化连接
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("[Cookie管理器] 启动...")

        if "RECHEME" not in self.config:
            logger.warning("[Cookie管理器] 配置中未找到 RECHEME 部分，跳过。")
            return

        self._user_instances = defaultdict(list)
        self._logged_cookies = set()
        self._logged_configs = set()
        self._cookie_success_logged = set()
        self._cookie_updates_batch = defaultdict(list)

        enabled_instances = []
        disabled_instances = []

        for rec_name, api_info_list in self.config["RECHEME"].items():
            if not isinstance(api_info_list, list):
                continue

            for i, api_info in enumerate(api_info_list):
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

    async def stop(self):
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
        logger.info("[Cookie管理器] 已停止。")
        self.tasks = {}

    def _get_effective_cookie_config(self, rec_name: str, api_info: dict) -> dict:
        """获取生效的 Cookie 配置 (实例覆盖全局)"""
        global_cookie_config = self.config.get("COOKIE", {})
        recheme_global_cookie_config = self.config.get("RECHEME", {}).get("COOKIE", {})
        instance_cookie_config = api_info.get("COOKIE", {})
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
        
        if not isinstance(global_c_conf, dict): global_c_conf = {}
        if not isinstance(recheme_global_c_conf, dict): recheme_global_c_conf = {}
        if not isinstance(instance_c_conf, dict): instance_c_conf = {}
        
        final_c_conf = global_c_conf.copy()
        final_c_conf.update(recheme_global_c_conf)
        final_c_conf.update(instance_c_conf)
        final_c_conf['ENABLE'] = True
        return final_c_conf

    async def _log_batch_results(self):
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

    async def _manage_instance(self, rec_name: str, recheme_api: RechemeAPI, cookie_config: dict):
        mode = cookie_config.get("MODE", "random")
        check_interval = cookie_config.get("CHECK_INTERVAL", 3600)
        random_interval = cookie_config.get("RANDOM_CHANGE_INTERVAL", 86400)
        cookie_server_url = cookie_config.get("VALUE")
        cookie_server_token = cookie_config.get("TOKEN")
        # 从配置中获取超时设置，默认为10秒
        request_timeout = cookie_config.get("REQUEST_TIMEOUT", 10)
        max_retries = cookie_config.get("MAX_RETRIES", 3)

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
                
                new_cookie = None
                current_dede_user_id = None

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
                    current_cookie_str = None
                    if mode == "random":
                       current_cookie_data_compare = await self._get_current_recheme_cookie(recheme_api)
                       if current_cookie_data_compare:
                            current_cookie_str = current_cookie_data_compare.get("cookie")
                    elif current_cookie_data:
                        current_cookie_str = current_cookie_data.get("cookie")

                    # 智能合并cookie，如果本地缺少buvid字段则添加
                    merged_cookie = self._merge_cookies_intelligently(current_cookie_str, new_cookie)
                    
                    if current_cookie_str is None or merged_cookie != current_cookie_str:
                        success = await self._update_recheme_cookie(recheme_api, merged_cookie)
                        if success:
                            uid_key = "random" if mode == "random" else current_dede_user_id
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

    async def _get_cookie_from_server(self, server_url: str, token: str, mode: str, dede_user_id: str = None, 
                                     timeout: int = 10, max_retries: int = 3) -> str | None:
        """
        从Cookie服务器获取Cookie，支持重试机制
        优先尝试 v2 API，失败(404)则回退到 v1 API
        
        Args:
            server_url: Cookie服务器地址
            token: 认证令牌
            mode: 获取模式 ('random' 或 'onlysync')
            dede_user_id: B站用户ID（仅在onlysync模式下使用）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        
        Returns:
            成功时返回Cookie字符串，失败时返回None
        """
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}" # v2 规范
            # v1 兼容: 有些旧服务可能仍检查 token header，保留以防万一，或者仅在 v1 fallback 时使用
            # 但标准 v2 要求 Authorization。旧 v1 代码使用 headers["token"] = token
        
        # 检查服务器健康状态
        health_key = f"{server_url}_{mode}"
        server_health = self._server_health[health_key]
        current_time = asyncio.get_event_loop().time()
        
        if server_health["backoff_until"] > current_time:
            backoff_remaining = round(server_health["backoff_until"] - current_time)
            logger.debug(f"[Cookie管理器] Cookie服务器 {server_url} 暂时不可用，{backoff_remaining}秒后重试")
            return None

        for retry in range(max_retries):
            if retry > 0:
                backoff_time = min(2 ** retry + random.uniform(0, 1), 60)
                logger.warning(f"[Cookie管理器] 请求Cookie服务器超时/错误，第{retry}次重试，等待{backoff_time:.2f}秒...")
                await asyncio.sleep(backoff_time)
            
            try:
                # -------------------------------------------------------
                # 尝试 v2 API
                # -------------------------------------------------------
                v2_url = ""
                v2_params = {}
                
                if mode == "random":
                    v2_url = urljoin(server_url, "/api/v1/cookies/random")
                    v2_params["format"] = "simple"
                elif mode == "onlysync" and dede_user_id:
                    v2_url = urljoin(server_url, f"/api/v1/cookies/{dede_user_id}")
                else:
                    logger.error(f"[Cookie管理器] 无效的模式或缺少DedeUserID")
                    return None

                try:
                    async with self.session.get(v2_url, headers=headers, params=v2_params, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # 解析 v2 响应
                            cookie_str = None
                            if mode == "random":
                                # simple format: {"DedeUserID": "...", "header_string": "..."}
                                cookie_str = data.get("header_string")
                            elif mode == "onlysync":
                                # full document: {"managed": {"header_string": "...", ...}, ...}
                                managed = data.get("managed", {})
                                cookie_str = managed.get("header_string")
                                if not cookie_str:
                                    # 尝试从顶层获取 (以防万一)
                                    cookie_str = data.get("header_string")

                            if cookie_str:
                                self._reset_server_health(health_key)
                                return cookie_str
                            else:
                                logger.warning(f"[Cookie管理器] v2 API 响应缺少 header_string: {data}")
                                # 这种情况下可能不是 API 版本问题，而是数据问题，但也可以尝试 v1 吗？
                                # 暂时认为 v2 响应了 200 但没数据就是没数据
                                return None
                        
                        elif response.status == 404:
                            # 404 说明可能不支持 v2 API，回退到 v1
                            logger.debug(f"[Cookie管理器] v2 API 返回 404，尝试回退到 v1 API")
                            raise FileNotFoundError("v2 API not found") # 触发内部异常以跳转到 v1 逻辑
                        else:
                            # 其他错误 (500, 401 等)
                            logger.warning(f"[Cookie管理器] v2 API 请求失败: {response.status}")
                            response.raise_for_status() # 抛出异常进入重试或退出
                
                except FileNotFoundError:
                    # -------------------------------------------------------
                    # 回退 v1 API
                    # -------------------------------------------------------
                    # v1 使用 token header
                    v1_headers = headers.copy()
                    if token:
                        v1_headers["token"] = token
                        # v1 通常不强制 Authorization Bearer，但也可能兼容。保留 token header 是关键。
                    
                    v1_url = ""
                    v1_params = {}
                    
                    if mode == "random":
                        v1_url = urljoin(server_url, "/api/cookie/random")
                        v1_params["type"] = "sim"
                    elif mode == "onlysync" and dede_user_id:
                        v1_url = urljoin(server_url, "/api/cookie")
                        v1_params["DedeUserID"] = dede_user_id
                    
                    async with self.session.get(v1_url, headers=v1_headers, params=v1_params, timeout=timeout) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        self._reset_server_health(health_key)
                        
                        if mode == "random":
                            if data.get("code") == 0 and data.get("cookie"):
                                return data["cookie"]
                            else:
                                logger.warning(f"[Cookie管理器] v1 获取随机Cookie失败: {data.get('message', '未知错误')}")
                                return None
                        elif mode == "onlysync":
                            return self._parse_v1_onlysync_response(data, dede_user_id)

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

    def _reset_server_health(self, health_key: str):
        server_health = self._server_health[health_key]
        server_health["failures"] = 0
        server_health["backoff_until"] = 0

    def _parse_v1_onlysync_response(self, data: dict, dede_user_id: str) -> str | None:
        """解析 v1 接口 onlysync 模式的响应"""
        cookie_parts = []
        required_cookies = {"DedeUserID", "SESSDATA", "bili_jct", "DedeUserID__ckMd5"}
        optional_cookies = {"buvid3", "buvid4"}
        found_cookies = {}
        is_valid = data.get("cookie_valid", False)
        has_cookie_info = "cookie_info" in data and isinstance(data["cookie_info"], dict) and "cookies" in data["cookie_info"] and isinstance(data["cookie_info"]["cookies"], list)

        if has_cookie_info:
            cookies_list = data["cookie_info"]["cookies"]
            for cookie_item in cookies_list:
                name = cookie_item.get("name")
                value = cookie_item.get("value")
                if (name in required_cookies or name in optional_cookies) and value:
                    found_cookies[name] = value

            all_required_found = required_cookies.issubset(found_cookies.keys())

            data_hash = hash(str(data.get("cookie_info", {})))
            log_key = f"cookie_checked_{dede_user_id}_{data_hash}"
            if log_key not in self._logged_cookies:
                status_msg = {
                    "valid": is_valid,
                    "has_cookie_info": has_cookie_info,
                    "all_required_found": all_required_found,
                    "found_keys": list(found_cookies.keys()) if found_cookies else []
                }
                logger.debug(f"[Cookie管理器] DedeUserID={dede_user_id} Cookie检查结果: {status_msg}")
                self._logged_cookies.add(log_key)

            if all_required_found:
                cookie_parts.append(f"DedeUserID={found_cookies['DedeUserID']}")
                cookie_parts.append(f"DedeUserID__ckMd5={found_cookies['DedeUserID__ckMd5']}")
                cookie_parts.append(f"SESSDATA={found_cookies['SESSDATA']}")
                cookie_parts.append(f"bili_jct={found_cookies['bili_jct']}")
                
                if "buvid3" in found_cookies:
                    cookie_parts.append(f"buvid3={found_cookies['buvid3']}")
                if "buvid4" in found_cookies:
                    cookie_parts.append(f"buvid4={found_cookies['buvid4']}")

                full_cookie = "; ".join(cookie_parts) + ";"
                
                success_log_key = f"cookie_success_{dede_user_id}_{data_hash}"
                if success_log_key not in self._cookie_success_logged:
                    logger.debug(f"[Cookie管理器] DedeUserID={dede_user_id}: 已成功获取并验证必需的 Cookie。")
                    self._cookie_success_logged.add(success_log_key)
                
                return full_cookie
            else:
                missing = required_cookies - found_cookies.keys()
                logger.warning(f"[Cookie管理器] DedeUserID={dede_user_id}: 缺少必需的Cookie项: {missing}。服务器响应中的键: {list(found_cookies.keys())}")
                return None
        else:
            logger.warning(f"[Cookie管理器] DedeUserID={dede_user_id}: Cookie服务器响应格式不正确或缺少 'cookie_info.cookies' 列表。")
            return None
    
    def _update_server_health(self, health_key: str):
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

    async def _get_current_recheme_cookie(self, recheme_api: RechemeAPI, silent: bool = False) -> dict | None:
        """获取录播姬当前的 Cookie 和 DedeUserID"""
        try:
            config_data = await recheme_api.get_global_config()

            if config_data and "optionalCookie" in config_data:
                cookie_str = config_data["optionalCookie"].get("value")
                if cookie_str:
                    parts = cookie_str.split(';')
                    dede_user_id = None
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

    def _merge_cookies_intelligently(self, current_cookie: str, new_cookie: str) -> str:
        """智能合并cookie，如果本地缺少buvid字段则从新cookie中添加"""
        if not current_cookie:
            return new_cookie
        if not new_cookie:
            return current_cookie
            
        # 解析当前cookie
        current_cookies = self._parse_cookie_string(current_cookie)
        new_cookies = self._parse_cookie_string(new_cookie)
        
        # 检查是否需要添加buvid字段
        buvid_fields = ['buvid3', 'buvid4']
        needs_update = False
        
        for field in buvid_fields:
            if field not in current_cookies and field in new_cookies:
                current_cookies[field] = new_cookies[field]
                needs_update = True
                logger.debug(f"[Cookie管理器] 添加缺失的{field}字段: {new_cookies[field][:20]}...")
        
        if needs_update:
            cookie_parts = []
            core_fields = ['DedeUserID', 'DedeUserID__ckMd5', 'SESSDATA', 'bili_jct']
            for field in core_fields:
                if field in current_cookies:
                    cookie_parts.append(f"{field}={current_cookies[field]}")
            
            # 添加buvid字段
            for field in buvid_fields:
                if field in current_cookies:
                    cookie_parts.append(f"{field}={current_cookies[field]}")
            
            # 添加其他字段
            for field, value in current_cookies.items():
                if field not in core_fields and field not in buvid_fields:
                    cookie_parts.append(f"{field}={value}")
            
            return "; ".join(cookie_parts) + ";"
        
        return current_cookie
    
    def _parse_cookie_string(self, cookie_str: str) -> dict:
        """解析cookie字符串为字典"""
        cookies = {}
        if not cookie_str:
            return cookies
            
        # 移除末尾的分号并分割
        parts = cookie_str.rstrip(';').split(';')
        for part in parts:
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        return cookies

    def _log_dede_user_id_details(self, dede_user_id: str):
        """记录 DedeUserID 及其关联实例的详细信息"""
        user_key = f"uid_{dede_user_id}"
        if user_key in self._user_instances:
            instances = self._user_instances[user_key]
            instances_count = len(instances)
            logger.debug(f"[Cookie管理器] DedeUserID={dede_user_id} ({instances_count}个实例): {', '.join(instances)}")
        else:
            logger.warning(f"[Cookie管理器] 尝试记录 DedeUserID={dede_user_id} 的详细信息，但未在实例列表中找到。")

    async def _update_recheme_cookie(self, recheme_api: RechemeAPI, new_cookie: str):
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