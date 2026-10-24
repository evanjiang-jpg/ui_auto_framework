# -*- coding: utf-8 -*-
"""
数据库访问客户端（单例）

支持的数据库类型（由 config/database.yaml 的 type 决定）：
  - sqlite     : 内置驱动，零依赖，默认用于本地/demo
  - mysql      : 需 pip install pymysql
  - postgresql : 需 pip install psycopg2-binary

统一约定：
  - 连接参数按环境从 database.yaml 读取，密码用 ${} 占位符由环境变量注入
  - 上层 SQL 一律使用 "?" 作为占位符，由本模块按数据库类型自动适配
  - readonly=true 的环境禁止任何写操作，防止误改线上数据
"""
import os
import threading
from typing import Any, Dict, List, Optional

from common.env_manager import config
from common.logger import get_logger

logger = get_logger("db_client")


class DatabaseClient:
    """数据库客户端单例"""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._conn = None
                    instance._db_type = None
                    instance._readonly = False
                    instance._cfg = {}
                    cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # 连接
    # ------------------------------------------------------------------
    def _load_cfg(self) -> Dict[str, Any]:
        cfg = config.load_layered_yaml("database.yaml")
        # sqlite 相对路径以工程根为基准
        if cfg.get("type", "sqlite") == "sqlite":
            path = cfg.get("database", "data/demo.db")
            if not os.path.isabs(path):
                cfg["database"] = os.path.join(config.project_root, path)
        return cfg

    def connect(self):
        """建立连接（幂等，重复调用返回同一连接）"""
        if self._conn is not None:
            return self._conn

        cfg = self._load_cfg()
        self._cfg = cfg
        self._db_type = cfg.get("type", "sqlite")
        self._readonly = bool(cfg.get("readonly", False))

        if self._db_type == "sqlite":
            import sqlite3
            db_path = cfg.get("database")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self._conn = sqlite3.connect(db_path, timeout=cfg.get("timeout", 10))
        elif self._db_type == "mysql":
            import pymysql
            self._conn = pymysql.connect(
                host=cfg.get("host"), port=cfg.get("port", 3306),
                user=cfg.get("user"), password=cfg.get("password", ""),
                database=cfg.get("database"), charset=cfg.get("charset", "utf8mb4"),
                connect_timeout=cfg.get("timeout", 10),
            )
        elif self._db_type == "postgresql":
            import psycopg2
            self._conn = psycopg2.connect(
                host=cfg.get("host"), port=cfg.get("port", 5432),
                user=cfg.get("user"), password=cfg.get("password", ""),
                dbname=cfg.get("database"), connect_timeout=cfg.get("timeout", 10),
            )
        else:
            raise ValueError(f"不支持的数据库类型: {self._db_type}")

        logger.info(f"数据库已连接：type={self._db_type} readonly={self._readonly}")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def reconnect(self) -> None:
        """环境切换后重新连接"""
        self.close()
        return self.connect()

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------
    @property
    def db_type(self) -> str:
        return self._db_type or self._load_cfg().get("type", "sqlite")

    @property
    def is_sqlite(self) -> bool:
        return self.db_type == "sqlite"

    @property
    def placeholder(self) -> str:
        """上层统一写 '?'，非 sqlite 由执行时转换为 '%s'"""
        return "?" if self.is_sqlite else "%s"

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def _cursor(self):
        conn = self.connect()
        return conn.cursor()

    def _adapt(self, sql: str) -> str:
        if self.is_sqlite:
            return sql
        return sql.replace("?", "%s")

    def _check_writable(self, sql: str) -> None:
        if self._readonly:
            head = sql.strip().split(None, 1)[0].lower() if sql.strip() else ""
            if head not in ("select", "show", "describe", "desc", "explain"):
                raise PermissionError(
                    f"当前环境数据库为只读（readonly=true），禁止执行写操作: {head.upper()}"
                )

    def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """查询多行，返回字典列表"""
        cur = self._cursor()
        cur.execute(self._adapt(sql), params or [])
        columns = [d[0] for d in (cur.description or [])]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return rows

    def query_one(self, sql: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        """查询单行，无结果返回 None"""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def query_value(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        """查询单个标量值"""
        row = self.query_one(sql, params)
        if not row:
            return None
        return list(row.values())[0]

    def execute(self, sql: str, params: Optional[List[Any]] = None) -> int:
        """执行写操作，返回受影响行数"""
        self._check_writable(sql)
        cur = self._cursor()
        cur.execute(self._adapt(sql), params or [])
        self._conn.commit()
        return cur.rowcount

    def executescript(self, sql_script: str) -> None:
        """执行一段多语句 SQL（主要用于 sqlite 初始化）"""
        self._check_writable("create")
        cur = self._cursor()
        if self.is_sqlite:
            cur.executescript(sql_script)
        else:
            for statement in filter(None, (s.strip() for s in sql_script.split(";"))):
                cur.execute(statement)
        self._conn.commit()

    def executescript_file(self, relative_path: str) -> None:
        """执行工程根下的 .sql 文件"""
        path = relative_path if os.path.isabs(relative_path) else os.path.join(config.project_root, relative_path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"SQL 文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            self.executescript(f.read())
        logger.debug(f"已执行 SQL 脚本: {path}")

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------
    def table_exists(self, table: str) -> bool:
        if self.is_sqlite:
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
            return self.query_one(sql, [table]) is not None
        sql = "SELECT table_name FROM information_schema.tables WHERE table_name=?"
        return self.query_one(sql, [table]) is not None

    def count(self, table: str, where: Optional[Dict[str, Any]] = None) -> int:
        """统计行数，where 为 {字段: 值} 的等值条件"""
        sql = f"SELECT COUNT(*) AS cnt FROM {table}"
        params: List[Any] = []
        if where:
            sql += " WHERE " + " AND ".join(f"{k} = {self.placeholder}" for k in where)
            params = list(where.values())
        return int(self.query_value(sql, params) or 0)

    def fetch_rows(self, table: str, where: Optional[Dict[str, Any]] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """按等值条件查行，供断言或调试使用"""
        sql = f"SELECT * FROM {table}"
        params: List[Any] = []
        if where:
            sql += " WHERE " + " AND ".join(f"{k} = {self.placeholder}" for k in where)
            params = list(where.values())
        sql += f" LIMIT {int(limit)}"
        return self.query(sql, params)


# 全局单例
db_client = DatabaseClient()
