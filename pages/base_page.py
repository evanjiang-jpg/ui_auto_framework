# -*- coding: utf-8 -*-
"""
页面对象基类

提供所有页面共用的能力：
  - 元素定位与基础操作（查找/输入/点击/取文本），内置显式等待
  - 登录态注入（跳过 UI 登录）
  - 登录态失效自动重登并重试一次

页面子类只声明自己的元素定位与业务动作，公共能力全部下沉到这里。
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common.env_manager import config
from common.logger import get_logger

logger = get_logger("base_page")


class BasePage:
    """页面对象基类"""

    def __init__(self, driver, auth=None):
        self.driver = driver
        self.auth = auth
        self.base_url = config.get("base_url", "")
        self.timeout = config.get("default_timeout", 10)
        self.poll = config.get("poll_interval", 0.5)

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------
    def open(self, path: str = "") -> "BasePage":
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}" if path else self.base_url
        logger.info(f"打开页面: {url}")
        self.driver.get(url)
        return self

    @property
    def current_url(self) -> str:
        return getattr(self.driver, "current_url", "")

    # ------------------------------------------------------------------
    # 元素操作
    # ------------------------------------------------------------------
    def find(self, locator, timeout: float = None):
        """显式等待元素出现并返回（替代隐式等待与 sleep）"""
        return WebDriverWait(self.driver, timeout or self.timeout, self.poll).until(
            EC.presence_of_element_located(locator)
        )

    def click(self, locator, timeout: float = None):
        element = WebDriverWait(self.driver, timeout or self.timeout, self.poll).until(
            EC.element_to_be_clickable(locator)
        )
        element.click()
        return self

    def type(self, locator, text: str):
        element = self.find(locator)
        element.clear()
        element.send_keys(text)
        return self

    def get_text(self, locator, timeout: float = None) -> str:
        return self.find(locator, timeout).text

    def is_visible(self, locator, timeout: float = 3) -> bool:
        try:
            self.find(locator, timeout)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 登录态
    # ------------------------------------------------------------------
    def inject_token(self, token: str) -> "BasePage":
        """把复用的 token 注入浏览器，跳过重复登录"""
        if not token:
            return self
        try:
            self.driver.execute_script(
                "window.localStorage.setItem('token', arguments[0]);", token
            )
        except Exception as e:
            logger.warning(f"注入 token 失败: {e}")
        return self

    def is_session_expired(self) -> bool:
        """判断是否被踢回登录页"""
        return "/login" in (self.current_url or "")

    def retry_after_relogin(self, action, *args, **kwargs):
        """执行 action；若登录态失效则自动重登、重新注入 token 并重试一次"""
        result = action(*args, **kwargs)
        if self.auth is not None and self.is_session_expired():
            logger.warning("检测到登录态失效，自动重登后重试")
            self.auth.ensure_valid()
            self.inject_token(self.auth.get_token())
            result = action(*args, **kwargs)
        return result
