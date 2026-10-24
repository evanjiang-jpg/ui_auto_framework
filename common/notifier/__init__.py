# -*- coding: utf-8 -*-
"""通知模块（分层：模型 / 模板 / 通道 / 门面）"""
from common.notifier.models import TestResult, parse_allure_results
from common.notifier.notifier import TestNotifier
from common.notifier.channels.dingtalk import send_dingtalk
from common.notifier.channels.email import send_email

__all__ = [
    "TestResult",
    "parse_allure_results",
    "TestNotifier",
    "send_dingtalk",
    "send_email",
]
