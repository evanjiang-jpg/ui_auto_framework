# -*- coding: utf-8 -*-
"""
订单模块用例

演示「上下游参数传递」的标准做法：
  - 上游（会话级 auth）产出的 token，下游用例以参数名 auth 直接取用
  - 需要跨页面/跨步骤共享时，同步进全局上下文，避免层层传参
  - 登录态失效时自动重登，并保证 token 随之更新
"""
import allure
import pytest

from pages.order_page import OrderPage
from common.global_context import context


@allure.epic("UI 自动化测试框架")
@allure.feature("订单模块")
class TestOrder:

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.order
    @allure.title("复用会话级登录态访问订单页，不重复登录")
    def test_order_list_with_session_auth(self, browser, auth):
        logins_before = auth.login_count

        token = auth.get_token()
        assert token, "会话级 auth 应已提供可用 token"
        assert context.get("login_token") == token, "token 应已同步到全局上下文，供跨页面读取"

        OrderPage(browser, auth=auth).inject_token(token).open_order_list()

        assert auth.login_count == logins_before, "会话内不应重复触发登录"

    @pytest.mark.p1
    @pytest.mark.order
    @allure.title("token 失效后自动重登并拿到新 token")
    def test_order_token_expired_relogin(self, browser, auth):
        before = auth.get_token()
        relogin_before = auth.relogin_count

        auth.invalidate()                 # 模拟被踢回登录页 / 收到 401
        after = auth.ensure_valid()       # 自动重登

        assert after, "重登后应拿到 token"
        assert after != before, "重登后 token 应发生变化"
        assert auth.relogin_count == relogin_before + 1, "应记录一次自动重登"

        OrderPage(browser, auth=auth).inject_token(after).open_order_list()
