# -*- coding: utf-8 -*-
"""飞书机器人通道：卡片消息 + 加签 + @人"""
import time
import hmac
import base64
import hashlib
import os
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
    """发送飞书卡片消息（与邮件同风格），返回是否成功"""
    if not webhook:
        logger.warning("未配置飞书 webhook，跳过")
        return False

    ctx = templates.build_context(result)
    ctx["at_emails"] = at_emails or []
    ctx["at_all"] = at_all

    is_success = result.is_success()
    header_template = "green" if is_success else "red"
    icon = "✅" if is_success else "❌"
    status_text = ctx["status_text"]
    env = ctx["env"].upper()
    executed_at = ctx["executed_at"]

    total = result.total
    passed = result.passed
    failed = result.failed
    broken = result.error
    skipped = result.skipped
    pass_rate = ctx["pass_rate"]
    duration = ctx["duration"]

    report_url = ctx.get("report_url") or result.report_url
    pipeline_url = ctx.get("pipeline_url") or result.build_url or os.getenv("CI_BUILD_URL", "")
    author = ctx.get("author", "") or result.commit_author or os.getenv("CI_COMMIT_AUTHOR", "")
    commit_msg = ctx.get("commit_msg", "") or os.getenv("CI_COMMIT_MSG", "")

    elements = []

    # ---------- 第一行：5 个大数字并排（用例总数 / 通过 / 失败 / 异常 / 跳过） ----------
    color_passed = "green" if passed > 0 else "default"
    color_failed = "red" if failed > 0 else "default"
    color_broken = "red" if broken > 0 else "default"

    def _num_column(label: str, value: int, color: str = "default") -> dict:
        if color == "green":
            num_content = f"<font color='green'>**{value}**</font>"
        elif color == "red":
            num_content = f"<font color='red'>**{value}**</font>"
        else:
            num_content = f"**{value}**"
        return {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{label}\n{num_content}",
                },
            }],
        }

    elements.append({
        "tag": "column_set",
        "flex_mode": "stretch",
        "columns": [
            _num_column("用例总数", total),
            _num_column("通过", passed, color_passed),
            _num_column("失败", failed, color_failed),
            _num_column("异常", broken, color_broken),
            _num_column("跳过", skipped),
        ],
    })

    # ---------- 第二行：通过率 + 耗时 ----------
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**通过率**: {pass_rate}% ｜ **总耗时**: {duration}s",
        },
    })

    # ---------- 第三行：按钮（报告 + 流水线） ----------
    buttons = []
    if report_url:
        buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📊 查看完整 Allure 报告"},
            "url": report_url,
            "type": "primary",
        })
    if pipeline_url:
        buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🔗 查看流水线详情"},
            "url": pipeline_url,
            "type": "default",
        })
    if buttons:
        elements.append({
            "tag": "action",
            "actions": buttons,
        })

    # ---------- 第四行：失败用例列表（有失败才显示） ----------
    failed_cases = ctx.get("failed_cases", [])
    if failed_cases:
        case_lines = []
        for case in failed_cases[:10]:
            name = case.get("name", "")
            msg = case.get("message", "")
            if msg:
                case_lines.append(f"- **{name}**: {msg}")
            else:
                case_lines.append(f"- **{name}**")
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**失败用例**\n" + "\n".join(case_lines),
            },
        })

    # ---------- 底部：流水线 ID / 触发者 / commit ----------
    footer_parts = []
    pipeline_id = ctx.get("pipeline_id") or os.getenv("CI_PIPELINE_ID", "")
    if pipeline_id:
        footer_parts.append(f"流水线 #{pipeline_id}")
    if author:
        footer_parts.append(f"提交人: {author}")
    if commit_msg:
        footer_parts.append(commit_msg[:60])
    if footer_parts:
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": " ｜ ".join(footer_parts)}],
        })

    # ---------- @人 ----------
    at_section = ""
    if at_all:
        at_section = '<at id=all></at>'
    elif at_emails:
        at_section = " ".join(f'<at email="{e}"></at>' for e in at_emails)
    if at_section:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": at_section},
        })

    title = f"{icon} UI自动化测试执行报告"
    header_subtitle = f"{status_text} ｜ 环境 {env} ｜ {executed_at}"

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": header_template,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": header_subtitle},
                },
                {"tag": "hr"},
            ] + elements,
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