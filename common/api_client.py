# -*- coding: utf-8 -*-
"""
接口客户端（单例）

用途：UI 用例的「接口前置 / 后置」
  - 接口造数据：建用户、建订单，比走 UI 快 5-10 倍且更稳
  - 接口登录  ：直接拿 token/cookie 注入浏览器，跳过 UI 登录流程
  - 接口清理  ：用例结束删除测试数据，不污染环境

特性：
  - base_url / timeout 每次请求时从配置读取，切换环境立即生效
  - 自动带 Authorization 头（从全局上下文取 token）
  - 收到 401 自动刷新 token 并重试一次
"""
import json
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from common.env_manager import config
from common.global_context import context
from common.logger import get_logger

logger = get_logger("api_client")


class APIClient:
    """接口请求客户端（单例，内置 requests.Session 复用连接）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._session = requests.Session()
            instance._init_headers()
            cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # 基础配置
    # ------------------------------------------------------------------
    @staticmethod
    def _base_url() -> str:
        return config.get("api_base_url") or config.get("base_url", "")

    @staticmethod
    def _timeout() -> int:
        return config.get("api_timeout", 10)

    def _init_headers(self) -> None:
        token = context.get("login_token")
        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})

    def _build_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self._base_url().rstrip('/')}/{path.lstrip('/')}"

    # ------------------------------------------------------------------
    # 请求
    # ------------------------------------------------------------------
    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self._build_url(path)
        kwargs.setdefault("timeout", self._timeout())
        self._log_request(method, url, kwargs)

        # 无真实后端时走内存桩（api_mock=true，真实项目置 false）
        if config.get("api_mock", False):
            from common.mock_api import mock_request
            response = mock_request(method, url, kwargs.get("json"))
            self._log_response(response)
            return response

        # token 失效自动重试一次
        attempts = int(config.get("api_retry_times", 2)) or 1
        response = None
        for i in range(attempts):
            response = self._session.request(method, url, **kwargs)
            if response.status_code == 401 and i < attempts - 1:
                logger.warning("接口返回 401，刷新 token 后重试")
                self.refresh_token()
                continue
            break

        self._log_response(response)
        return response

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # 登录态
    # ------------------------------------------------------------------
    def set_token(self, token: str) -> None:
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        context.set("login_token", token)

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        for name, value in (cookies or {}).items():
            self._session.cookies.set(name, value)

    def refresh_token(self) -> Optional[str]:
        """刷新 token：真实项目按自己接口重写（如调 /api/refresh）"""
        logger.warning("refresh_token 未实现，请在项目中按实际接口重写")
        return None

    def login_by_api(self, username: str, password: str,
                     login_path: str = "/api/login") -> Tuple[Any, Dict[str, str]]:
        """接口登录，返回 (token, cookies)，用于注入浏览器跳过 UI 登录"""
        start = time.time()
        resp = self.post(login_path, json={"username": username, "password": password})
        if resp.status_code != 200:
            raise RuntimeError(f"接口登录失败：{resp.status_code} {resp.text}")

        data = resp.json()
        token = (data.get("data") or {}).get("token")
        if token:
            self.set_token(token)
        cookies = {c.name: c.value for c in resp.cookies}
        self.set_cookies(cookies)
        logger.info(f"接口登录完成，耗时 {time.time() - start:.2f}s（比 UI 登录快 3-5 倍）")
        return token, cookies

    def inject_auth_to_browser(self, driver) -> None:
        """把接口登录拿到的 cookie 注入 selenium 浏览器，跳过登录页"""
        base_url = self._base_url()
        if not base_url:
            raise RuntimeError("未配置 base_url，无法注入 cookie")

        domain = urlparse(base_url).netloc
        try:
            driver.get(f"{base_url}/favicon.ico")  # 必须先访问同域名才能写 cookie
        except Exception as e:
            logger.warning(f"注入 cookie 前的预热访问失败（继续尝试）: {e}")

        for name, value in self._session.cookies.items():
            try:
                driver.add_cookie({"name": name, "value": value, "domain": domain})
            except Exception as e:
                logger.warning(f"注入 cookie {name} 失败: {e}")
        logger.info("登录态已注入浏览器，可直接访问业务页")

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    @staticmethod
    def _log_request(method: str, url: str, kwargs: Dict[str, Any]) -> None:
        logger.debug(f"[API Request] {method.upper()} {url}")
        if kwargs.get("params"):
            logger.debug(f"  params: {kwargs['params']}")
        if kwargs.get("json"):
            logger.debug(f"  body: {json.dumps(kwargs['json'], ensure_ascii=False)}")

    @staticmethod
    def _log_response(response: requests.Response) -> None:
        logger.debug(
            f"[API Response] {response.status_code} {response.elapsed.total_seconds():.2f}s"
        )
        try:
            logger.debug(f"  resp: {json.dumps(response.json(), ensure_ascii=False)[:500]}")
        except Exception:
            logger.debug(f"  resp: {response.text[:500]}")


# 全局单例
api_client = APIClient()
