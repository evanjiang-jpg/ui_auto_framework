# -*- coding: utf-8 -*-
"""
钩子点：全部 fixture 集中管理

分层关系（scope 必须从窄到宽，否则触发 ScopeMismatch）：
    clean_context(function, autouse)  —— 每条用例前后清理上下文
    db_assert(function) -> db(session) —— 数据库断言器 -> 连接
    browser(function)   -> auth/api_login(session)
                                      —— 浏览器 -> 会话级登录态

要点：auth 是 session 级，绝不依赖 function 级的 browser；
它内部自行创建一个临时 driver 完成一次登录，登录后立即关闭，只保留 token。
"""
import pytest

from common.env_manager import config
from common.global_context import context
from common.browser_factory import create_driver, quit_driver
from common.auth_manager import AuthManager
from common.api_client import api_client
from common.logger import logger
from common.db import db_client, DatabaseAsserter
from pages.base_page import BasePage
from pages.login_page import LoginPage


# ======================================================================
# 上下文：每条用例执行前后自动清理，避免参数污染
# ======================================================================
@pytest.fixture(autouse=True)
def clean_context():
    context.clear()
    yield
    context.clear()


# ======================================================================
# 登录态：会话级，整个会话只真正登录一次
# ======================================================================
@pytest.fixture(scope="session")
def auth():
    """UI 登录:会话级登录态管理器

    - 内部自建临时 driver 完成一次真实登录，随后关闭，只保留 token
    - 下游用例以参数名 auth 取用，可直接 auth.get_token()
    - token 失效时 auth.ensure_valid() 自动重登
    """
    temp_driver = create_driver()
    login_page = LoginPage(temp_driver)

    manager = AuthManager(
        login_func=lambda: login_page.do_login_and_get_token(
            config.get("common_user"), config.get("common_pwd")
        ),
        logout_func=lambda: logger.info("会话结束，清理登录态"),
        validate_func=lambda token: bool(token),
    )
    manager.login()
    logger.info(f"会话级登录完成，token={manager.token}，登录次数={manager.login_count}")

    quit_driver(temp_driver)   # 登录完即可关闭这个临时浏览器
    yield manager
    manager.logout()


# ======================================================================
# 接口登录：session 级，--api-login 时启用
# ======================================================================
class ApiLoginSession:
    """接口登录会话：持有接口登录拿到的 token/cookies
    设计亮点:开关 + 懒加载 + 缓存 三位一体：
    """

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.token = None
        self.cookies = {}

    def ensure(self) -> bool:
        """注入登录态:确保已通过接口登录，返回是否可用 ->确保登录成功，懒加载"""
        if not self.enabled:
            return False
        if self.token:
            return True
        username = config.get("common_user")
        password = config.get("common_pwd")
        self.token, self.cookies = api_client.login_by_api(username, password)
        return True


@pytest.fixture(scope="session")
def api_login(pytestconfig):
    return ApiLoginSession(enabled=pytestconfig.getoption("api_login"))


# ======================================================================
# 浏览器：每条用例独立 driver，自动注入登录态
# ======================================================================
@pytest.fixture(scope="function")
def browser(auth, api_login):
    """功能级浏览器 fixture

    优先用接口登录态（--api-login），否则复用会话级 UI 登录 token，
    从而跳过每条用例都走一遍登录页的耗时操作。
    """
    driver = create_driver()
    page = BasePage(driver)

    try:
        if api_login.ensure():
            api_client.inject_auth_to_browser(driver)
            logger.debug("已注入接口登录态")
        else:
            token = auth.get_token()
            if token:
                page.inject_token(token)
    except Exception as e:
        logger.warning(f"注入登录态失败（用例可自行登录）: {e}")

    yield driver
    quit_driver(driver)


# ======================================================================
# 接口前置：用例前造数据，用例后自动清理
# ======================================================================
@pytest.fixture(scope="function")
def api_setup():
    """接口前置 fixture

    用法::
        def test_xxx(browser, api_setup):
            user = api_setup.create_user()
            order = api_setup.create_order(user_id=user["id"], product_id=1)
    """
    created_resources = []

    class ApiSetup:
        @staticmethod
        def create_user(username=None, password="Test@123", **kwargs):
            import uuid
            username = username or f"test_user_{uuid.uuid4().hex[:8]}"
            resp = api_client.post("/api/user/create", json={
                "username": username, "password": password, **kwargs
            })
            user = (resp.json() or {}).get("data", {}) or {}
            if user.get("id"):
                created_resources.append(("user", user["id"]))
            logger.info(f"[接口前置] 创建用户 {username}, id={user.get('id')}")
            return user

        @staticmethod
        def create_order(user_id, product_id, amount=99.0, **kwargs):
            resp = api_client.post("/api/order/create", json={
                "user_id": user_id, "product_id": product_id,
                "amount": amount, **kwargs
            })
            order = (resp.json() or {}).get("data", {}) or {}
            if order.get("id"):
                created_resources.append(("order", order["id"]))
            logger.info(f"[接口前置] 创建订单 id={order.get('id')}, 用户={user_id}")
            return order

        @staticmethod
        def delete_user(user_id):
            api_client.delete(f"/api/user/{user_id}")
            logger.info(f"[接口后置] 删除用户 {user_id}")

        @staticmethod
        def delete_order(order_id):
            api_client.delete(f"/api/order/{order_id}")
            logger.info(f"[接口后置] 删除订单 {order_id}")

    yield ApiSetup()

    # 后置清理：逆序删除，且不因清理失败影响用例结论
    for res_type, res_id in reversed(created_resources):
        try:
            if res_type == "user":
                api_client.delete(f"/api/user/{res_id}")
            else:
                api_client.delete(f"/api/order/{res_id}")
            logger.info(f"[接口后置] 已清理 {res_type} id={res_id}")
        except Exception as e:
            logger.warning(f"[接口后置] 清理 {res_type} id={res_id} 失败: {e}")


# ======================================================================
# 数据库：session 级连接 + 功能级断言器
# ======================================================================
@pytest.fixture(scope="session")
def db(pytestconfig):
    """会话级数据库连接（sqlite demo 会按需初始化表结构）"""
    db_client.connect()
    if db_client.is_sqlite:
        try:
            db_client.executescript_file("data/schema.sql")
            logger.debug("sqlite demo 表结构与种子数据已就绪")
        except Exception as e:
            logger.warning(f"初始化 sqlite 表结构失败: {e}")
    yield db_client
    db_client.close()


@pytest.fixture(scope="function")
def db_assert(db):
    """数据库断言器"""
    return DatabaseAsserter(db)
