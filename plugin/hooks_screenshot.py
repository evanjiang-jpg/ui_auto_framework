# -*- coding: utf-8 -*-
"""
钩子点：用例失败自动捕获现场

两个关键设计：
  1. 零业务侵入：用例里不需要写任何 try/except，失败现场由钩子统一捕获
  2. 重试不重复截图：配合 pytest-rerunfailures，只有「最后一次仍失败」才截图，
     避免同一用例重试 3 次就产出 3 张重复截图，把报告塞满噪音

失败现场包含三件套：截图（本地 + Allure 内嵌）、页面源码、异常堆栈。
"""
import pytest

from common.screenshot import capture_failure
from common.logger import get_logger

logger = get_logger("hooks_screenshot")

# 常见的 driver fixture 名称，按顺序尝试
_DRIVER_FIXTURE_NAMES = ("browser", "driver", "chrome", "webdriver")


def _find_driver(item):
    """从用例已注入的 fixture 里找出浏览器实例"""
    funcargs = getattr(item, "funcargs", None) or {}
    for name in _DRIVER_FIXTURE_NAMES:
        if name in funcargs and funcargs[name] is not None:
            return funcargs[name]
    # 兜底：任何具备 save_screenshot 的对象
    for value in funcargs.values():
        if hasattr(value, "save_screenshot"):
            return value
    return None


def _effective_reruns(item) -> int:
    """本用例实际生效的重试次数：命令行 --reruns 与 flaky marker 取较大者"""
    reruns = int(getattr(item.config.option, "reruns", 0) or 0)
    marker = item.get_closest_marker("flaky")
    if marker:
        reruns = max(reruns, int(marker.kwargs.get("reruns", 0) or 0))
    return reruns


def _has_more_retry(item) -> bool:
    """判断该用例后面是否还有重试机会（有则本次不截图）"""
    reruns = _effective_reruns(item)
    if reruns <= 0:
        return False
    # pytest-rerunfailures 每重试一次 execution_count +1
    execution_count = int(getattr(item, "execution_count", 1) or 1)
    return execution_count <= reruns


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """用例 setup/call 阶段失败时自动捕获失败现场"""
    outcome = yield
    report = outcome.get_result()

    if report.when not in ("setup", "call"):
        return
    if not report.failed:
        return

    if _has_more_retry(item):
        logger.debug(f"{item.name} 仍有重试机会，本次失败不截图")
        return

    driver = _find_driver(item)
    # excinfo 从 makereport 的 call 参数取最稳（report.excinfo 在某些版本上可能为空）
    excinfo = getattr(call, "excinfo", None) or getattr(report, "excinfo", None)
    capture_failure(driver, item.name, excinfo)
