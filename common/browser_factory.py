# -*- coding: utf-8 -*-
"""
浏览器工厂：把「创建哪个 driver」这件事收拢到一处

由配置 use_stub_browser 决定：
  - true  ：返回内置桩驱动，用于无 GUI 环境演示（默认，方便开箱跑通）
  - false ：返回真实 Chrome，接入真实项目时改成这个
"""
from common.env_manager import config
from common.logger import get_logger

logger = get_logger("browser")


def _create_chrome():
    """创建真实 Chrome driver（需要本机装好 Chrome/ChromeDriver）"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if config.get("headless", True):
        options.add_argument("--headless=new")
    for arg in (
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--ignore-certificate-errors",
        f"--window-size={config.get('window_size', '1920,1080')}",
    ):
        options.add_argument(arg)

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(config.get("implicit_wait", 10))
    driver.set_page_load_timeout(config.get("page_load_timeout", 30))
    return driver


def _create_stub():
    """创建演示用桩驱动"""
    from common.stub_driver import StubDriver
    logger.info("使用桩驱动 StubDriver（use_stub_browser=true，接入真实项目请置为 false）")
    return StubDriver(base_url=config.get("base_url", ""))


def create_driver():
    """按配置创建 driver 实例"""
    if config.get("use_stub_browser", True):
        driver = _create_stub()
    else:
        driver = _create_chrome()

    base_url = config.get("base_url", "")
    if base_url:
        try:
            driver.get(base_url)
        except Exception as e:
            logger.warning(f"打开 base_url 失败（继续执行）: {e}")
    return driver


def quit_driver(driver) -> None:
    """安全关闭 driver"""
    if driver is None:
        return
    try:
        driver.quit()
    except Exception as e:
        logger.warning(f"关闭浏览器失败: {e}")
