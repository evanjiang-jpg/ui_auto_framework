# -*- coding: utf-8 -*-
"""
演示用桩驱动 StubDriver

为什么单独抽成文件：
  早期版本把桩驱动写在 testcases/test_login.py 里覆盖 conftest 的 browser fixture，
  导致用例文件被框架细节污染；现在改为由配置开关 use_stub_browser 控制，
  用例文件保持干净，接入真实项目时只需把配置改成 false。

它模拟 selenium WebDriver 的最小可用接口（含显式等待依赖的 is_displayed /
is_enabled 等），不打开任何浏览器，用于在无 GUI 环境（CI 容器、沙箱）演示框架能力。
"""
import base64

# 1x1 透明 PNG，作为截图占位
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


class StubElement:
    """桩元素：兼容 selenium 显式等待所需的元素接口"""

    def __init__(self, text: str = ""):
        self.text = text
        self.clicked = False
        self.attributes = {}

    # ---------- 状态判断（显式等待会调用） ----------
    def is_displayed(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def is_selected(self) -> bool:
        return False

    # ---------- 操作 ----------
    def clear(self):
        self.text = ""

    def send_keys(self, value):
        self.text = str(value)

    def click(self):
        self.clicked = True

    def get_attribute(self, name):
        return self.attributes.get(name, "")

    @property
    def tag_name(self):
        return "input"

    # ---------- 子元素 ----------
    def find_element(self, *args, **kwargs):
        return StubElement("")

    def find_elements(self, *args, **kwargs):
        return []


class StubDriver:
    """模拟 selenium driver 的最小接口"""

    def __init__(self, base_url: str = ""):
        self.current_url = base_url or "about:blank"
        self.title = "Stub 页面"
        self.page_source = "<html><body><h1>Stub 页面</h1></body></html>"
        self.name = "stub"
        self._cookies = []
        self._storage = {}
        self._elements = {}

    # ---------- 导航 ----------
    def get(self, url):
        self.current_url = url

    def quit(self):
        pass

    def close(self):
        pass

    # ---------- 窗口/等待相关（真实 driver 有，这里空实现以兼容调用） ----------
    def implicitly_wait(self, seconds):
        pass

    def set_page_load_timeout(self, seconds):
        pass

    def set_window_size(self, width, height):
        pass

    def maximize_window(self):
        pass

    @property
    def current_window_handle(self):
        return "stub-window"

    # ---------- 页面信息 ----------
    def save_screenshot(self, path):
        with open(path, "wb") as f:
            f.write(_PNG_1X1)
        return True

    def execute_script(self, script, *args):
        # 仅支持 demo 用到的 localStorage 读写
        if "setItem" in script and args:
            self._storage[self._extract_key(script)] = args[0]
            return None
        if "getItem" in script:
            return self._storage.get(self._extract_key(script))
        return None

    @staticmethod
    def _extract_key(script: str) -> str:
        for quote in ("'", '"'):
            if quote in script:
                parts = script.split(quote)
                if len(parts) >= 2:
                    return parts[1]
        return ""

    # ---------- 元素 ----------
    def register_element(self, locator, element: StubElement):
        """测试代码可预先注册元素，模拟页面上已存在的元素"""
        self._elements[locator] = element

    def find_element(self, by, value=None):
        locator = (by, value) if value is not None else by
        if locator in self._elements:
            return self._elements[locator]
        # 未注册则返回一个空桩元素，保证不抛异常
        element = StubElement("")
        self._elements[locator] = element
        return element

    def find_elements(self, by, value=None):
        try:
            return [self.find_element(by, value)]
        except Exception:
            return []

    # ---------- Cookie ----------
    def add_cookie(self, cookie_dict):
        self._cookies.append(cookie_dict)

    def get_cookies(self):
        return list(self._cookies)

    def delete_all_cookies(self):
        self._cookies.clear()
