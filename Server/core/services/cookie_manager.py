import asyncio, aiohttp, copy
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

    async def start(self):
        if self.running:
            return
        self.running = True
        self.session = aiohttp.ClientSession()
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
                        current_dede_user_id
                    )

                if new_cookie:
                    current_cookie_str = None
                    if mode == "random":
                       current_cookie_data_compare = await self._get_current_recheme_cookie(recheme_api)
                       if current_cookie_data_compare:
                            current_cookie_str = current_cookie_data_compare.get("cookie")
                    elif current_cookie_data:
                        current_cookie_str = current_cookie_data.get("cookie")

                    if current_cookie_str is None or new_cookie != current_cookie_str:
                        success = await self._update_recheme_cookie(recheme_api, new_cookie)
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

    async def _get_cookie_from_server(self, server_url: str, token: str, mode: str, dede_user_id: str = None) -> str | None:
        headers = {}
        if token:
            headers["token"] = token

        target_url = ""
        params = {}

        try:
            if mode == "random":
                target_url = urljoin(server_url, "/api/cookie/random")
                params["type"] = "sim"
                async with self.session.get(target_url, headers=headers, params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("code") == 0 and data.get("cookie"):
                        return data["cookie"]
                    else:
                        logger.error(f"[Cookie管理器] 获取随机Cookie失败: {data.get('message', '未知错误')}")
                        return None
            elif mode == "onlysync" and dede_user_id:
                target_url = urljoin(server_url, "/api/cookie")
                params["DedeUserID"] = dede_user_id
                async with self.session.get(target_url, headers=headers, params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()

                    cookie_parts = []
                    required_cookies = {"DedeUserID", "SESSDATA", "bili_jct", "DedeUserID__ckMd5"}
                    found_cookies = {}
                    is_valid = data.get("cookie_valid", False)
                    has_cookie_info = "cookie_info" in data and isinstance(data["cookie_info"], dict) and "cookies" in data["cookie_info"] and isinstance(data["cookie_info"]["cookies"], list)

                    if has_cookie_info:
                        cookies_list = data["cookie_info"]["cookies"]
                        for cookie_item in cookies_list:
                            name = cookie_item.get("name")
                            value = cookie_item.get("value")
                            if name in required_cookies and value:
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
            else:
                 logger.error(f"[Cookie管理器] 无效的模式或缺少DedeUserID")
                 return None

        except aiohttp.ClientError as e:
            logger.error(f"[Cookie管理器] 请求Cookie服务器失败: {e}")
            return None
        except Exception as e:
            logger.error(f"[Cookie管理器] 处理响应失败: {e}", exc_info=True)
            return None

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