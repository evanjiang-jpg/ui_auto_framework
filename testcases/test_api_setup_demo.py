# -*- coding: utf-8 -*-
"""
接口前置用例

演示 UI 自动化里的「接口造数」用法：
  - 用例开始前通过接口创建用户/订单，用例结束自动清理，不污染环境
  - 相比走 UI 造数据，速度提升 5-10 倍，且不受页面改版影响

说明：演示环境无真实后端，配置 api_mock=true 时请求由内存桩响应；
真实项目把 api_mock 改为 false，本用例代码无需改动。
"""
import allure
import pytest


@allure.epic("UI 自动化测试框架")
@allure.feature("接口前置")
class TestApiSetupDemo:

    @pytest.mark.p1
    @pytest.mark.api
    @allure.title("接口前置创建用户与订单")
    def test_create_data_by_api(self, browser, api_setup):
        user = api_setup.create_user()
        assert user.get("id"), "接口前置应返回用户 id"

        order = api_setup.create_order(user_id=user["id"], product_id=1001, amount=199.0)
        assert order.get("id"), "接口前置应返回订单 id"
        assert order["user_id"] == user["id"], "订单应关联到刚创建的用户"

    @pytest.mark.p1
    @pytest.mark.api
    @allure.title("接口前置支持自定义账号参数")
    def test_create_user_with_custom_name(self, browser, api_setup):
        user = api_setup.create_user(username="custom_user_001", nickname="自定义用户")
        assert user.get("username") == "custom_user_001"
