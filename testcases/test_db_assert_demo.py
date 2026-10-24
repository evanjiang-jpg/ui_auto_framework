# -*- coding: utf-8 -*-
"""
数据库断言用例

演示 UI 自动化里的「数据层校验」：
  - UI 操作后校验数据库里的数据确实变了（比只看页面文字可靠得多）
  - 异步最终一致性：UI 已提示成功但数据异步落库，用 wait_for_* 轮询等待

演示配置为 sqlite（零依赖），真实项目把 config/database.yaml 改成 mysql 即可，
用例代码完全不变。
"""
import uuid

import allure
import pytest


@allure.epic("UI 自动化测试框架")
@allure.feature("数据库断言")
class TestDbAssertDemo:

    @pytest.mark.p1
    @pytest.mark.db
    @allure.title("校验种子数据存在")
    def test_seed_data_exists(self, db, db_assert):
        row = db_assert.assert_row_exists("users", {"username": "demo_user"})
        assert row["status"] == "active"
        db_assert.assert_column_value("users", "nickname", "演示用户", {"username": "demo_user"})

    @pytest.mark.p1
    @pytest.mark.db
    @allure.title("新增数据后可断言存在，并正确统计条数")
    def test_insert_then_assert(self, db, db_assert):
        username = f"auto_{uuid.uuid4().hex[:8]}"
        db.execute(
            "INSERT INTO users (username, nickname, status) VALUES (?, ?, ?)",
            [username, "自动化新增", "active"],
        )
        try:
            db_assert.assert_row_exists("users", {"username": username})
            db_assert.assert_row_count("users", 1, {"username": username})
            db_assert.assert_column_value("users", "status", "active", {"username": username})
        finally:
            db.execute("DELETE FROM users WHERE username = ?", [username])

    @pytest.mark.p1
    @pytest.mark.db
    @allure.title("异步落库场景用轮询等待断言")
    def test_wait_for_row(self, db, db_assert):
        username = f"async_{uuid.uuid4().hex[:8]}"
        db.execute(
            "INSERT INTO users (username, nickname, status) VALUES (?, ?, ?)",
            [username, "异步落库", "active"],
        )
        try:
            row = db_assert.wait_for_row("users", {"username": username}, timeout=5)
            assert row["username"] == username
        finally:
            db.execute("DELETE FROM users WHERE username = ?", [username])

    @pytest.mark.p2
    @pytest.mark.db
    @allure.title("数据不存在时断言应失败")
    def test_assert_not_exists(self, db, db_assert):
        db_assert.assert_row_not_exists("users", {"username": "not_exist_user_xxx"})

    @pytest.mark.p2
    @pytest.mark.db
    @allure.title("订单表种子数据校验")
    def test_order_seed(self, db, db_assert):
        db_assert.assert_row_exists("orders", {"id": 1})
        db_assert.assert_column_value("orders", "status", "paid", {"id": 1})
