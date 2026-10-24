# -*- coding: utf-8 -*-
"""
上下文容器：跨用例 / 跨步骤 / 跨页面共享业务参数

提供两种实现，按并行方式二选一：
  - GlobalContext      : 全局共享一份 dict，写操作加锁。
                         适用于单线程 + pytest-xdist 多进程（进程天然隔离）
  - ThreadLocalContext : 每个线程各自一份 dict，读到的永远是自己写的值。
                         适用于同一进程内多线程并发驱动多个浏览器

统一导出 ``context``（默认全局版），如用多线程请改为 ThreadLocalContext()。
"""
import threading
from typing import Any, Dict


class GlobalContext:
    """全局上下文单例（线程安全写入）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._context = {}
                    cls._instance = instance
        return cls._instance

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._context[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def delete(self, key: str) -> None:
        with self._lock:
            self._context.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._context.clear()

    def get_all(self) -> Dict[str, Any]:
        return self._context.copy()


class ThreadLocalContext:
    """线程隔离上下文：每个线程一份独立参数，彻底避免并行串数据"""

    def __init__(self):
        self._local = threading.local()

    @property
    def _data(self) -> Dict[str, Any]:
        if not hasattr(self._local, "data"):
            self._local.data = {}
        return self._local.data

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def get_all(self) -> Dict[str, Any]:
        return self._data.copy()


# 默认使用全局上下文；多线程场景请替换为 ThreadLocalContext()
context = GlobalContext()
