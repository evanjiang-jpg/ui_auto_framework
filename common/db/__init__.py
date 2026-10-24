# -*- coding: utf-8 -*-
"""数据库能力：连接访问 + 断言，供 UI 用例做数据层校验"""
from common.db.db_client import DatabaseClient, db_client
from common.db.assertion import DatabaseAsserter, DBAssertionError

__all__ = ["DatabaseClient", "db_client", "DatabaseAsserter", "DBAssertionError"]
