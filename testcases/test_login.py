# -*- coding: utf-8 -*-
"""
登录模块用例

演示三类能力：
  1. 基础登录流程（PO 模式）
  2. 数据驱动：数据放 yaml / json，代码零硬编码，标签自动生成
  3. 会话级登录态复用（auth fixture）
"""
import allure
import pytest

from pages.login_page import LoginPage
from common.data_reader import load_test_data

# 数据源：可省略后缀（自动识别 yaml/json），也可显式指定
login_data = load_test_data("login_test_data")
boundary_data = load_test_data("login_boundary_data.json")


@allure.epic("UI 自动化测试框架")
@allure.feature("登录模块")
class TestLogin:

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.login
    @allure.title("正确账号密码登录成功")
    def test_login_success(self, browser):
        token = LoginPage(browser).do_login_and_get_token("13800138000", "test123")
        assert token, "登录成功应返回非空 token"
        assert token.startswith("token_"), f"token 格式异常: {token}"

    @pytest.mark.p0
    @pytest.mark.login
    @pytest.mark.parametrize("case", login_data, ids=lambda c: c["case_name"])
    def test_login_data_driven(self, browser, case):
        """数据驱动：标签、优先级、描述全部来自数据文件，代码里不写装饰器"""
        page = LoginPage(browser)
        if case["expect_success"]:
            token = page.do_login_and_get_token(case["username"], case["password"])
            assert token, f"用例[{case['case_name']}] 应登录成功"
        else:
            with pytest.raises(ValueError):
                page.do_login_and_get_token(case["username"], case["password"])

    @pytest.mark.p1
    @pytest.mark.login
    @pytest.mark.parametrize("case", boundary_data, ids=lambda c: c["case_name"])
    def test_login_boundary(self, browser, case):
        """边界值用例：数据源为 json，演示多格式数据源支持

        账号长度校验由页面对象承担（LoginPage.USERNAME_LENGTH），
        用例只按数据文件里的期望值做断言。
        """
        page = LoginPage(browser)
        if case["expect_success"]:
            assert page.do_login_and_get_token(case["username"], case["password"])
        else:
            with pytest.raises(ValueError):
                page.do_login_and_get_token(case["username"], case["password"])

    @pytest.mark.p1
    @pytest.mark.login
    @allure.title("会话级登录态只登录一次")
    def test_session_login_only_once(self, browser, auth):
        """auth 是 session 级 fixture，整个会话只真正登录一次"""
        assert auth.get_token(), "应能从会话级 auth 拿到 token"
        assert auth.login_count == 1, f"整个会话应只登录一次，实际 {auth.login_count} 次"
