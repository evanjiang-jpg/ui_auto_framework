# -*- coding: utf-8 -*-
"""
稳定性与重试工具 —— UI 自动化抖动治理的统一入口

UI 自动化 90% 的不稳定来自两类原因：
  1. 时序问题：元素还没渲染出来、接口数据还没落库、异步状态还没流转
  2. 偶发抖动：网络瞬断、服务短暂 5xx

本模块把这两类问题的标准解法收拢成三个函数，避免每个页面/用例各写一套 sleep：

  wait_until()      条件轮询等待：满足条件立刻返回，超时才报错（替代 sleep）
  wait_for_value()  等待某个取值变成期望结果：接口数据落库、订单状态流转等
  retry_call()      通用重试：指数退避、异常白名单、可回调

说明：用例级"失败重跑"由 pytest-rerunfailures 承担（见 pytest.ini 的 flaky 标记），
本模块负责的是「用例内部的等待与重试」。
"""
import time
from typing import Any, Callable, Iterable, Optional, Tuple, Type

from common.logger import logger


class WaitTimeoutError(AssertionError):
    """等待超时：继承 AssertionError，让 pytest 直接判定为失败而不是 error"""


class RetryExhaustedError(Exception):
    """重试次数耗尽"""


def wait_until(
    predicate: Callable[[], Any],
    timeout: float = 10,
    interval: float = 0.5,
    message: str = "",
    raise_on_timeout: bool = True,
) -> bool:
    """轮询等待 predicate 返回真值

    :param predicate: 无参可调用对象，返回真值即视为条件满足
    :param timeout:   超时时间（秒）
    :param interval:  轮询间隔（秒）
    :param message:   超时时附加到异常里的说明
    :param raise_on_timeout: 超时是抛异常（默认）还是返回 False
    """
    deadline = time.time() + timeout
    last_error: Optional[Exception] = None
    while time.time() < deadline:
        try:
            if predicate():
                return True
        except Exception as e:  # 轮询期间允许元素未找到等异常，继续重试
            last_error = e
        time.sleep(interval)

    if raise_on_timeout:
        detail = f"（最后异常：{last_error}）" if last_error else ""
        raise WaitTimeoutError(
            f"等待超时 {timeout}s{('：' + message) if message else ''}{detail}"
        )
    return False


def wait_for_value(
    getter: Callable[[], Any],
    expected: Any,
    timeout: float = 10,
    interval: float = 0.5,
    comparator: Optional[Callable[[Any, Any], bool]] = None,
    message: str = "",
) -> Any:
    """等待 getter() 的返回值满足期望，返回最后一次取到的值

    :param comparator: 自定义比较函数 compare(actual, expected) -> bool；
                       默认使用 ==
    """
    compare = comparator or (lambda actual, exp: actual == exp)
    box = {"value": None}

    def _check():
        value = getter()
        box["value"] = value
        return compare(value, expected)

    wait_until(
        _check,
        timeout=timeout,
        interval=interval,
        message=message or f"期望值 {expected!r}，实际始终为 {box['value']!r}",
    )
    return box["value"]


def retry_call(
    func: Callable[..., Any],
    *args,
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Iterable[Type[BaseException]] = (Exception,),
    on_retry: Optional[Callable[[int, BaseException], None]] = None,
    **kwargs,
) -> Any:
    """通用重试：失败后按指数退避重试，直到成功或次数耗尽

    :param attempts:   总尝试次数（含首次），>=1
    :param delay:      首次重试前等待秒数
    :param backoff:    退避倍数，每次重试等待 = 上次 * backoff
    :param exceptions: 触发重试的异常类型
    :param on_retry:   回调 on_retry(第几次, 异常)，用于打日志/截图
    """
    if attempts < 1:
        raise ValueError("attempts 必须 >= 1")

    wait = delay
    last_error: Optional[BaseException] = None

    for attempt in range(1, attempts + 1):
        try:
            return func(*args, **kwargs)
        except tuple(exceptions) as e:
            last_error = e
            if attempt == attempts:
                break
            if on_retry:
                on_retry(attempt, e)
            logger.warning(
                f"第 {attempt}/{attempts - 1} 次重试：{func.__name__} 失败 - {e}，"
                f"{wait:.1f}s 后重试"
            )
            time.sleep(wait)
            wait *= backoff

    raise RetryExhaustedError(
        f"{getattr(func, '__name__', func)} 重试 {attempts} 次仍失败：{last_error}"
    ) from last_error
