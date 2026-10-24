# -*- coding: utf-8 -*-
"""钉钉机器人通道：Markdown 消息 + 加签 + @人"""
import time
import hmac
import base64
import hashlib
import urllib.parse
from typing import List, Optional

import requests

from common.logger import get_logger
from common.notifier.models import TestResult
from common.notifier import templates

logger = get_logger("notify_dingtalk")


def _sign(secret: str, timestamp: str) -> str:
    """钉钉官方加签算法：HmacSHA256(timestamp + '\n' + secret, secret) -> base64 -> urlencode"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))


def send_dingtalk(
    result: TestResult,
    webhook: str,
    secret: str = "",
    at_mobiles: Optional[List[str]] = None,
    at_all: bool = False,
    timeout: int = 10,
) -> bool:
    """发送钉钉 Markdown 消息，返回是否成功"""
    if not webhook:
        logger.warning("未配置钉钉 webhook，跳过")
        return False

    ctx = templates.build_context(result)
    ctx["at_mobiles"] = at_mobiles or ctx["at_mobiles"]
    ctx["at_all"] = at_all or ctx["at_all"]
    text = templates.render("dingtalk.md.j2", ctx)

    url = webhook
    if secret:
        timestamp = str(round(time.time() * 1000))
        url = f"{webhook}&timestamp={timestamp}&sign={_sign(secret, timestamp)}"

    payload = {
        "msgtype": "markdown",
        "markdown": {"title": f"UI自动化测试通知 - {ctx['status_text']}", "text": text},
        "at": {"atMobiles": ctx["at_mobiles"], "isAtAll": ctx["at_all"]},
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        data = resp.json()
        if data.get("errcode") == 0:
            logger.info("钉钉通知发送成功")
            return True
        logger.error(f"钉钉通知发送失败: {data}")
        return False
    except Exception as e:
        logger.error(f"钉钉通知发送异常: {e}")
        return False
