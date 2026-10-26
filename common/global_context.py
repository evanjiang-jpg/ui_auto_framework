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
    # 双重检查锁（Double-Checked Locking）线程安全单例模式
    # 三个写方法都加锁，保证对 _context 这个全局唯一的 dict 的所有修改都是串行的、不会丢失。
    # 两个读方法不加锁，靠 CPython GIL 保证安全，换性能。
    # __new__ 是静态方法，在对象分配内存之前运行，
    # 返回值就是最终创建的对象。这样可以保证无论调用 GlobalContext() 多少次，拿到的都是同一个实例：
    # 把单例逻辑写在 __init__ 里，每次调用 GlobalContext() 都会先 __new__ 分配一块新内存，然后 __init__ 里虽然能返回旧实例，但那块新内存已经浪费了（Python GC 会回收）。
    

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
# """_context 是类级别单例创建时初始化的那一个 dict（__new__ 里 instance._context = {}）。
# 这里就是往这个全局唯一的字典里写一个键值对。"""
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._context[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

# """保证删除操作的原子性"""
    def delete(self, key: str) -> None:
        with self._lock:
            self._context.pop(key, None)

    
    def clear(self) -> None:
        with self._lock:
            self._context.clear()

    def get_all(self) -> Dict[str, Any]:
        return self._context.copy()
# """如果要彻底隔离需要 copy.deepcopy，
# 但自动化测试里 context 存的通常都是字符串、数字这类不可变值，浅拷贝够用了"""

class ThreadLocalContext:
# """线程隔离上下文：每个线程一份独立参数，彻底避免并行串数据"""

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
