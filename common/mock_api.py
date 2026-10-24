# -*- coding: utf-8 -*-
"""
接口桩后端（演示用）

UI 自动化框架常需要接口前置造数据，但演示环境没有真实后端。
本模块提供一个内存桩：把 /api/** 的请求按路径返回结构化假数据，
让接口前置、接口登录等能力开箱即可跑通。

开关：config/environments.yaml 的 api_mock
  - true  ：走本桩（默认，演示用）
  - false ：走真实接口

真实项目把 api_mock 置为 false 即可，本模块不会被触发。
"""
import json
import time
import itertools
from datetime import timedelta
from typing import Any, Dict, Optional

from requests.cookies import RequestsCookieJar


_ID_SEQ = itertools.count(1001)


class MockResponse:
    """模拟 requests.Response 的最小接口"""

    def __init__(self, status_code: int, payload: Dict[str, Any],
                 cookies: Optional[RequestsCookieJar] = None):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)
        self.elapsed = timedelta(milliseconds=12)
        self.cookies = cookies or RequestsCookieJar()

    def json(self) -> Dict[str, Any]:
        return self._payload


def _mock_login(body: Dict[str, Any]) -> MockResponse:
    username = body.get("username") or "mock_user"
    jar = RequestsCookieJar()
    jar.set("SESSION", f"mock_session_{username}")
    return MockResponse(200, {
        "code": 0,
        "message": "success",
        "data": {"token": f"mock_token_{username}_{int(time.time())}"},
    }, cookies=jar)


def _mock_create_user(body: Dict[str, Any]) -> MockResponse:
    user_id = next(_ID_SEQ)
    return MockResponse(200, {
        "code": 0,
        "message": "success",
        "data": {
            "id": user_id,
            "username": body.get("username", f"mock_user_{user_id}"),
            "status": "active",
        },
    })


def _mock_create_order(body: Dict[str, Any]) -> MockResponse:
    order_id = next(_ID_SEQ)
    return MockResponse(200, {
        "code": 0,
        "message": "success",
        "data": {
            "id": order_id,
            "user_id": body.get("user_id"),
            "product_id": body.get("product_id"),
            "amount": body.get("amount", 0),
            "status": "created",
        },
    })


def mock_request(method: str, url: str, body: Optional[Dict[str, Any]] = None) -> MockResponse:
    """按 方法 + 路径 返回桩响应"""
    method = method.upper()
    body = body or {}
    path = url.split("?")[0].rstrip("/")

    if method == "POST" and path.endswith("/api/login"):
        return _mock_login(body)
    if method == "POST" and path.endswith("/api/user/create"):
        return _mock_create_user(body)
    if method == "POST" and path.endswith("/api/order/create"):
        return _mock_create_order(body)
    if method in ("DELETE", "PUT"):
        return MockResponse(200, {"code": 0, "message": "success", "data": {}})

    return MockResponse(200, {"code": 0, "message": "success", "data": {}})
