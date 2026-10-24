# -*- coding: utf-8 -*-
"""
通知门面（唯一对外入口）

职责只有「读配置 + 调度通道 + 汇总结果」，具体渲染和发送分别由
templates.py 与 channels/ 承担，保持单一职责。
"""
import os
from typing import Dict

from common.logger import get_logger
from common.notifier.models import TestResult
from common.notifier.channels.dingtalk import send_dingtalk
from common.notifier.channels.email import send_email

logger = get_logger("notifier")


def _split_env(name: str) -> list:
    raw = os.getenv(name, "") or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def _to_bool(name: str, default: bool = False) -> bool:
    return (os.getenv(name, str(default)).lower() == "true")


class TestNotifier:
    """测试结果通知器：按 .env 配置决定启用哪些通道"""

    def __init__(self):
        self.ding_enabled = _to_bool("DINGTALK_ENABLED")
        self.email_enabled = _to_bool("EMAIL_ENABLED")

        self.ding_cfg = {
            "webhook": os.getenv("DINGTALK_WEBHOOK", ""),
            "secret": os.getenv("DINGTALK_SECRET", ""),
            "at_mobiles": _split_env("DINGTALK_AT_MOBILES"),
            "at_all": _to_bool("DINGTALK_AT_ALL"),
        }
        self.email_cfg = {
            "host": os.getenv("EMAIL_SMTP_HOST", ""),
            "port": int(os.getenv("EMAIL_SMTP_PORT", "465") or 465),
            "ssl": _to_bool("EMAIL_SMTP_SSL", True),
            "user": os.getenv("EMAIL_USER", ""),
            "pwd": os.getenv("EMAIL_PASSWORD", ""),
            "sender": os.getenv("EMAIL_SENDER", ""),
            "receivers": _split_env("EMAIL_RECEIVERS"),
            "cc": _split_env("EMAIL_CC"),
        }

    def send(self, result: TestResult, attach_report_dir: str = "") -> Dict[str, bool]:
        """发送通知，返回各通道成功与否；单通道异常不影响其它通道"""
        results: Dict[str, bool] = {}

        if self.ding_enabled:
            try:
                results["dingtalk"] = send_dingtalk(result, **self.ding_cfg)
            except Exception as e:
                logger.error(f"钉钉通知异常: {e}")
                results["dingtalk"] = False

        if self.email_enabled:
            try:
                results["email"] = send_email(
                    result,
                    smtp_host=self.email_cfg["host"],
                    smtp_port=self.email_cfg["port"],
                    use_ssl=self.email_cfg["ssl"],
                    user=self.email_cfg["user"],
                    password=self.email_cfg["pwd"],
                    sender=self.email_cfg["sender"],
                    receivers=self.email_cfg["receivers"],
                    cc=self.email_cfg["cc"],
                    attach_report_dir=attach_report_dir,
                )
            except Exception as e:
                logger.error(f"邮件通知异常: {e}")
                results["email"] = False

        if not results:
            logger.info("未启用任何通知通道，跳过通知")
        return results
