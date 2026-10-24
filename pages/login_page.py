# -*- coding: utf-8 -*-
"""登录页对象"""
import uuid

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from common.logger import get_logger

logger = get_logger("login_page")


class LoginPage(BasePage):
    """登录页"""

    # ---------- 元素定位 ----------
    username_input = (By.ID, "username")
    password_input = (By.ID, "password")
    login_button = (By.ID, "loginBtn")
    welcome_tip = (By.CLASS_NAME, "welcome")
    error_tip = (By.CLASS_NAME, "error")

    # ---------- 业务动作 ----------
    def open_login(self) -> "LoginPage":
        self.open("/login")
        return self

    def input_username(self, username: str) -> "LoginPage":
        self.type(self.username_input, username)
        return self

    def input_password(self, password: str) -> "LoginPage":
        self.type(self.password_input, password)
        return self

    def click_login(self) -> "LoginPage":
        self.click(self.login_button)
        return self

    def login(self, username: str, password: str) -> "LoginPage":
        self.open_login()
        self.input_username(username)
        self.input_password(password)
        self.click_login()
        return self

    # 演示系统的账号规则：手机号 11 位（真实项目按自己的规则调整）
    USERNAME_LENGTH = 11

    def validate_credentials(self, username: str, password: str) -> None:
        """登录前置校验：必填 + 账号格式"""
        if not username:
            raise ValueError("登录用户名不能为空")
        if not password:
            raise ValueError("登录密码不能为空")
        if len(username) < self.USERNAME_LENGTH:
            raise ValueError(
                f"账号长度不足 {self.USERNAME_LENGTH} 位：{username}"
            )

    def do_login_and_get_token(self, username: str, password: str) -> str:
        """供会话级 auth fixture 调用：执行一次真实登录并返回 token

        真实项目里 token 从 cookie 或 localStorage 读取，例如：
            return self.driver.execute_script("return window.localStorage.getItem('token');")
        demo 环境无真实后端，这里生成一个可辨识的 token 以便演示复用与重登。
        """
        self.validate_credentials(username, password)
        self.login(username, password)
        token = f"token_{uuid.uuid4().hex[:10]}"
        self.inject_token(token)
        logger.info(f"登录成功，用户={username}")
        return token

    def do_logout(self) -> None:
        logger.info("执行登出")
        self.open("/logout")

    def get_welcome_text(self) -> str:
        return self.get_text(self.welcome_tip)

    def get_error_text(self) -> str:
        return self.get_text(self.error_tip)
