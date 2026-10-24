# -*- coding: utf-8 -*-
"""
重试与稳定性用例

演示 UI 自动化抖动治理的三个层次：
  L1 用例内等待   —— wait_until / wait_for_value，替代 sleep，条件满足即返回
  L2 用例内重试   —— retry_call，针对网络瞬断等偶发异常做指数退避重试
  L3 用例级重跑   —— @pytest.mark.flaky(reruns=N)，整条用例失败后自动重跑

注意 L3：配合 plugin/hooks_screenshot.py，重试的中间失败不会重复截图，
只有最后一次仍失败才捕获现场，避免报告被重复截图刷屏。
"""
import allure
import pytest

from common.retry import wait_until, wait_for_value, retry_call, WaitTimeoutError

# 跨执行累加，用于演示「首次失败、重试后成功」的抖动场景
_RETRY_ATTEMPT = {"count": 0}


@allure.epic("UI 自动化测试框架")
@allure.feature("重试与稳定性")
class TestRetryDemo:

    @pytest.mark.p1
    @pytest.mark.regression
    @allure.title("条件轮询等待：满足即返回，不必死等")
    def test_wait_until(self):
        state = {"n": 0}

        def condition():
            state["n"] += 1
            return state["n"] >= 3

        assert wait_until(condition, timeout=5, interval=0.05)
        assert state["n"] == 3, "条件满足后应立即返回，不该继续轮询"

    @pytest.mark.p1
    @pytest.mark.regression
    @allure.title("等待某个取值变成期望值")
    def test_wait_for_value(self):
        state = {"status": "created"}
        state["status"] = "paid"          # 模拟状态流转
        value = wait_for_value(lambda: state["status"], "paid", timeout=2, interval=0.05)
        assert value == "paid"

    @pytest.mark.p1
    @pytest.mark.regression
    @allure.title("通用重试：前两次失败，第三次成功")
    def test_retry_call(self):
        state = {"n": 0}

        def flaky_action():
            state["n"] += 1
            if state["n"] < 3:
                raise RuntimeError("模拟网络瞬断")
            return "success"

        assert retry_call(flaky_action, attempts=5, delay=0.01) == "success"
        assert state["n"] == 3

    @pytest.mark.p2
    @pytest.mark.regression
    @allure.title("等待超时应明确失败")
    def test_wait_until_timeout(self):
        with pytest.raises(WaitTimeoutError):
            wait_until(lambda: False, timeout=0.3, interval=0.05)

    @pytest.mark.p2
    @pytest.mark.flaky(reruns=1, reruns_delay=0)
    @allure.title("偶发失败用例：标记 flaky 后自动重跑直至成功")
    def test_flaky_case_auto_rerun(self):
        _RETRY_ATTEMPT["count"] += 1
        assert _RETRY_ATTEMPT["count"] >= 2, (
            "首次执行故意失败，验证 pytest-rerunfailures 会自动重跑（报告里显示 R）"
        )

    @pytest.mark.p2
    @pytest.mark.regression
    @allure.title("重试次数耗尽应抛出明确异常")
    def test_retry_exhausted(self):
        from common.retry import RetryExhaustedError

        def always_fail():
            raise RuntimeError("持续失败")

        with pytest.raises(RetryExhaustedError):
            retry_call(always_fail, attempts=2, delay=0.01)
