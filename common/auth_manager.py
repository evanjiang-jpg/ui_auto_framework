# -*- coding: utf-8 -*-
"""
登录态（token）管理器 —— 配合 session 级 fixture 使用

解决的问题：
  1. 整个测试会话只真正登录一次，后续用例复用缓存 token
  2. 登录态失效（401 / 被踢回登录页）时自动重登
  3. 并发取 token 时用锁内二次判断，保证只登录一次

与 fixture 的结合见 plugin/fixtures.py 的 auth fixture。
"""
import threading
from typing import Any, Callable, Optional

from common.api_client import TOKEN_CONTEXT_KEY
from common.global_context import context


class AuthManager:
    """会话级登录态管理器（线程安全）"""

    def __init__(
        self,
        login_func: Callable[[], Any],
        logout_func: Optional[Callable[[], None]] = None,
        validate_func: Optional[Callable[[Any], bool]] = None,
        token_key: str = TOKEN_CONTEXT_KEY,
    ):
        self._login_func = login_func
        self._logout_func = logout_func
        # 默认校验：token 非空即有效；真实项目改成「请求轻量接口 / 检查过期时间」
        self._validate_func = validate_func or (lambda token: token is not None)
        self._token_key = token_key

        self._token: Optional[Any] = None
        self._lock = threading.RLock()   # 可重入，login 内部再取锁不会死锁
        self.login_count = 0             # 真实登录次数
        self.relogin_count = 0           # 失效触发的自动重登次数
        self._invalidated = False        # 是否被显式标记失效（如收到 401）

    @property
    def token(self) -> Optional[Any]:
        return self._token

    def login(self) -> Any:
        """真正执行一次登录，缓存 token 并写入全局上下文"""
        with self._lock:
            self._token = self._login_func()
            self.login_count += 1
            self._invalidated = False
            context.set(self._token_key, self._token)
            return self._token

    def get_token(self, force_refresh: bool = False) -> Any:
        """下游取 token：有缓存直接复用，没有（或强制刷新）才登录

        注意两点：
          1. 锁内二次判断：并发首次取 token 时只会登录一次
          2. 返回前同步一次全局上下文 —— 上下文可能被用例级清理钩子清空，
             这里补写，保证下游始终能从 context 读到当前登录态
        """
        if force_refresh:
            return self.login()
        with self._lock:
            if self._token is None:
                return self.login()
            context.set(self._token_key, self._token)
            return self._token

    def invalidate(self) -> None:
        """标记登录态失效（明确收到 401 / 被踢回登录页时调用）"""
        with self._lock:
            self._token = None
            self._invalidated = True

    def ensure_valid(self) -> Any:
        """执行前校验登录态：有效直接返回，失效则自动重登一次"""
        with self._lock:
            if self._token is not None and self._validate_func(self._token):
                return self._token
            # 两种失效来源都计一次自动重登：
            #   1) token 还在但校验不通过（如已过期）
            #   2) 已被 invalidate() 显式标记失效（如收到 401）
            if self._invalidated or self._token is not None:
                self.relogin_count += 1
            self._token = None
        return self.login()

    def logout(self) -> None:
        """会话结束登出并清理缓存"""
        try:
            if self._logout_func:
                self._logout_func()
        finally:
            with self._lock:
                self._token = None
                context.delete(self._token_key)