# -*- coding: utf-8 -*-
"""订单页对象（下游页面，演示跨页面复用会话级登录态）"""
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from common.global_context import context


class OrderPage(BasePage):
    """订单页"""

    order_list = (By.CLASS_NAME, "orderList")
    order_item = (By.CLASS_NAME, "orderItem")

    def open_order_list(self) -> "OrderPage":
        """进入订单列表；token 失效会被踢回登录页，这里自动重登后重试"""
        self.open("/order")
        self.retry_after_relogin(self.driver.get, f"{self.base_url}/order")
        return self

    def get_current_user(self):
        """从上下文读取当前登录用户，无需层层传参"""
        return context.get("login_user")

    def get_order_count(self) -> int:
        try:
            return len(self.driver.find_elements(*self.order_item))
        except Exception:
            return 0
