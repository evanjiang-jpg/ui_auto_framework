# -*- coding: utf-8 -*-
"""
数据库断言

UI 用例常见的两类数据校验：
  1. UI 操作后，数据库里的数据确实变了（如修改昵称、下单成功）
  2. 异步最终一致性：UI 已提示成功，但数据异步落库，需要等一会儿才查得到

对应提供：
  assert_*       立即断言，查不到就失败
  wait_for_*     轮询等待，超时才失败（专治异步落库/最终一致）

所有 where 条件一律参数化，避免 SQL 注入，也避免拼字符串出错。
"""
import time
from typing import Any, Dict, Optional

from common.db.db_client import DatabaseClient, db_client
from common.logger import get_logger

logger = get_logger("db_assertion")


class DBAssertionError(AssertionError):
    """数据库断言失败：继承 AssertionError，让 pytest 判定为用例失败"""


class DatabaseAsserter:
    """数据库断言器"""

    def __init__(self, client: Optional[DatabaseClient] = None):
        self.db = client or db_client

    # ------------------------------------------------------------------
    # 基础查询
    # ------------------------------------------------------------------
    def get_row(self, table: str, where: Optional[Dict[str, Any]] = None,
                order_by: Optional[str] = None) -> Optional[Dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        params = []
        if where:
            sql += " WHERE " + " AND ".join(f"{k} = {self.db.placeholder}" for k in where)
            params = list(where.values())
        if order_by:
            sql += f" ORDER BY {order_by}"
        sql += " LIMIT 1"
        return self.db.query_one(sql, params)

    def count(self, table: str, where: Optional[Dict[str, Any]] = None) -> int:
        return self.db.count(table, where)

    # ------------------------------------------------------------------
    # 立即断言
    # ------------------------------------------------------------------
    def assert_row_exists(self, table: str, where: Optional[Dict[str, Any]] = None,
                          message: str = "") -> Dict[str, Any]:
        """断言表中存在符合条件的记录，并返回该行"""
        row = self.get_row(table, where)
        if row is None:
            raise DBAssertionError(
                message or f"断言失败：表 {table} 中不存在满足 {where} 的记录"
            )
        return row

    def assert_row_not_exists(self, table: str, where: Optional[Dict[str, Any]] = None,
                              message: str = "") -> None:
        """断言表中不存在符合条件的记录"""
        if self.get_row(table, where) is not None:
            raise DBAssertionError(
                message or f"断言失败：表 {table} 中不应存在满足 {where} 的记录"
            )

    def assert_row_count(self, table: str, expected: int,
                         where: Optional[Dict[str, Any]] = None, message: str = "") -> None:
        """断言记录数等于期望值"""
        actual = self.count(table, where)
        if actual != expected:
            raise DBAssertionError(
                message or f"断言失败：表 {table} 记录数期望 {expected}，实际 {actual}（条件 {where}）"
            )

    def assert_column_value(self, table: str, column: str, expected: Any,
                            where: Optional[Dict[str, Any]] = None, message: str = "") -> None:
        """断言某行某列的值等于期望值"""
        row = self.get_row(table, where)
        if row is None:
            raise DBAssertionError(
                message or f"断言失败：表 {table} 中不存在满足 {where} 的记录，无法校验 {column}"
            )
        actual = row.get(column)
        if actual != expected:
            raise DBAssertionError(
                message or f"断言失败：表 {table}.{column} 期望 {expected!r}，实际 {actual!r}"
                f"（条件 {where}）"
            )

    # ------------------------------------------------------------------
    # 轮询等待（异步最终一致）
    # ------------------------------------------------------------------
    def wait_for_row(self, table: str, where: Optional[Dict[str, Any]] = None,
                     timeout: float = 10, interval: float = 0.5,
                     message: str = "") -> Dict[str, Any]:
        """轮询等待记录出现，超时才失败"""
        deadline = time.time() + timeout
        row = None
        while time.time() < deadline:
            row = self.get_row(table, where)
            if row is not None:
                return row
            time.sleep(interval)
        raise DBAssertionError(
            message or f"等待超时 {timeout}s：表 {table} 中始终没有满足 {where} 的记录"
        )

    def wait_for_column_value(self, table: str, column: str, expected: Any,
                              where: Optional[Dict[str, Any]] = None,
                              timeout: float = 10, interval: float = 0.5,
                              message: str = "") -> Any:
        """轮询等待某列的值变成期望值（如订单状态由「待支付」流转为「已支付」）"""
        deadline = time.time() + timeout
        actual = None
        while time.time() < deadline:
            row = self.get_row(table, where)
            if row is not None:
                actual = row.get(column)
                if actual == expected:
                    return actual
            time.sleep(interval)
        raise DBAssertionError(
            message or f"等待超时 {timeout}s：表 {table}.{column} 期望 {expected!r}，"
            f"实际 {actual!r}（条件 {where}）"
        )

    def wait_for_count(self, table: str, expected: int,
                       where: Optional[Dict[str, Any]] = None,
                       timeout: float = 10, interval: float = 0.5,
                       message: str = "") -> int:
        """轮询等待记录数达到期望值"""
        deadline = time.time() + timeout
        actual = self.count(table, where)
        while time.time() < deadline:
            actual = self.count(table, where)
            if actual == expected:
                return actual
            time.sleep(interval)
        raise DBAssertionError(
            message or f"等待超时 {timeout}s：表 {table} 记录数期望 {expected}，"
            f"实际 {actual}（条件 {where}）"
        )
