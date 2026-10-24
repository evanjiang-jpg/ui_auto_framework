# -*- coding: utf-8 -*-
"""
失败现场捕获工具：截图 + 页面源码 + 堆栈，统一挂到 Allure 报告

设计要点：
  - 只做「捕获动作」，不关心何时触发（触发时机由 plugin/hooks_screenshot.py 决定）
  - 截图既落本地（给邮件/日志引用），又内嵌 Allure（失败用例点开即见图）
  - 所有异常都吞掉并记日志：截图失败绝不能影响用例本身的结论
"""
import os
import time
from typing import Optional

import allure

from common.env_manager import config
from common.logger import get_logger

logger = get_logger("screenshot")

try:
    from selenium.common.exceptions import WebDriverException
except ImportError:  # 未安装 selenium 时仍可导入本模块
    class WebDriverException(Exception):
        pass


def _screenshot_dir() -> str:
    raw = config.get("screenshot_dir", "screenshots")
    path = raw if os.path.isabs(raw) else os.path.join(config.project_root, raw)
    os.makedirs(path, exist_ok=True)
    return path


def _safe_name(test_name: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in test_name) or "case"


def capture_screenshot(driver, test_name: str) -> str:
    """捕获失败截图：本地落盘 + 内嵌 Allure，返回本地路径（失败返回空串）"""
    if driver is None:
        return ""
    file_path = os.path.join(
        _screenshot_dir(), f"{_safe_name(test_name)}_{time.strftime('%Y%m%d_%H%M%S')}.png"
    )
    try:
        driver.save_screenshot(file_path)
        with open(file_path, "rb") as f:
            allure.attach(
                f.read(),
                name=f"失败截图_{test_name}",
                attachment_type=allure.attachment_type.PNG,
            )
        logger.error(f"已捕获失败截图: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"截图失败（driver 可能已关闭）: {e}")
        return ""


def capture_page_source(driver, test_name: str) -> str:
    """失败时保存页面源码，便于排查元素定位问题"""
    if driver is None:
        return ""
    file_path = os.path.join(
        _screenshot_dir(), f"{_safe_name(test_name)}_{time.strftime('%Y%m%d_%H%M%S')}.html"
    )
    try:
        source = driver.page_source
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(source)
        allure.attach(
            source,
            name=f"失败页面源码_{test_name}",
            attachment_type=allure.attachment_type.HTML,
        )
        return file_path
    except Exception as e:
        logger.error(f"保存页面源码失败: {e}")
        return ""


def attach_traceback(excinfo) -> None:
    """把异常堆栈作为文本附件挂到 Allure"""
    if not excinfo:
        return
    import traceback
    try:
        text = "".join(
            traceback.format_exception(excinfo.type, excinfo.value, excinfo.tb)
        )
        allure.attach(text, name="异常堆栈", attachment_type=allure.attachment_type.TEXT)
    except Exception as e:
        logger.warning(f"挂载异常堆栈失败: {e}")


def capture_failure(driver, test_name: str, excinfo=None) -> None:
    """失败现场一次性捕获：截图 + 源码 + 堆栈"""
    capture_screenshot(driver, test_name)
    capture_page_source(driver, test_name)
    attach_traceback(excinfo)
