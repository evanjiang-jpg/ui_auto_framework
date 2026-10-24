# -*- coding: utf-8 -*-
"""飞书机器人通道：卡片消息 + 加签 + @人"""
import time
import hmac
import base64
import hashlib
from typing import List, Optional

import requests

from common.logger import get_logger
from common.notifier.models import TestResult
from common.notifier import templates

logger = get_logger("notify_feishu")


def _sign(secret: str, timestamp: str) -> str:
    """飞书加签算法：base64(hmac-sha256(timestamp + '\n' + secret))"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def send_feishu(
    result: TestResult,
    webhook: str,
    secret: str = "",
    at_emails: Optional[List[str]] = None,
    at_all: bool = False,
    timeout: int = 10,
) -> bool:
    """发送飞书卡片消息，返回是否成功"""
    if not webhook:
        logger.warning("未配置飞书 webhook，跳过")
        return False

    ctx = templates.build_context(result)
    ctx["at_emails"] = at_emails or []
    ctx["at_all"] = at_all

    status_color = "green" if result.failed == 0 and result.error == 0 else "red"
    status_text = ctx["status_text"]
    env = ctx["env"]
    total = result.total
    passed = result.passed
    failed = result.failed
    skipped = result.skipped
    pass_rate = ctx["pass_rate"]
    build_url = ctx.get("build_url", "")
    author = ctx.get("commit_author", "")
    commit_msg = ctx.get("commit_msg", "")

    at_section = ""
    if at_all:
        at_section = '<at id=all></at>'
    elif at_emails:
        at_section = " ".join(f'<at email="{e}"></at>' for e in at_emails)

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**环境**: {env}  \n"
                    f"**用例总数**: {total}  \n"
                    f"**通过**: <font color='green'>{passed}</font>  \n"
                    f"**失败**: <font color='red'>{failed}</font>  \n"
                    f"**跳过**: {skipped}  \n"
                    f"**通过率**: {pass_rate}%"
                ),
            },
        }
    ]

    if build_url:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看流水线详情"},
                "url": build_url,
                "type": "primary",
            }],
        })

    if author or commit_msg:
        footer_text = ""
        if author:
            footer_text += f"触发者: {author}"
        if commit_msg:
            footer_text += f"  |  {commit_msg[:50]}"
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": footer_text.strip()}],
        })

    if at_section:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": at_section},
        })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"UI自动化测试执行通知 - {status_text}"},
                "template": status_color,
            },
            "elements": elements,
        },
    }

    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = _sign(secret, timestamp)

    try:
        resp = requests.post(webhook, json=payload, timeout=timeout)
        data = resp.json()
        if data.get("code") == 0:
            logger.info("飞书通知发送成功")
            return True
        logger.error(f"飞书通知发送失败: {data}")
        return False
    except Exception as e:
        logger.error(f"飞书通知发送异常: {e}")
        return False