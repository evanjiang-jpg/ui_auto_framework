# -*- coding: utf-8 -*-
"""
多环境配置管理器（全工程唯一的配置入口）

职责：
  1. 环境解析  —— 命令行 -e > 环境变量 ENV > local.yaml 指定 > 默认环境
  2. 分层合并  —— default 层 + 当前环境层 + local.yaml 本地覆盖层
  3. 占位符注入 —— 配置值里的 ${VAR} 自动从环境变量取值（密钥不进仓库）
  4. 启动校验  —— 必填 key 缺失时立刻报错，不等到用例执行时才炸
  5. 通用读取  —— 除主配置外，还可加载其它分层 yaml（如 database.yaml）

对外只有一个单例：``from common.env_manager import config``
"""
import os
import re
import copy
import threading
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv


_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


class EnvManager:
    """多环境配置管理单例（线程安全）"""

    _instance = None
    _lock = threading.RLock()

    # ---------- 框架与配置文件之间的协议常量 ----------
    #: 当前环境的环境变量名（run.py / env_manager.py 共用，改一处全局生效）
    ENV_VAR = "ENV"
    #: 主配置文件名（相对 config/ 目录）
    MAIN_CONFIG_FILE = "environments.yaml"
    #: 本地个人覆盖层文件名（相对 config/ 目录）
    LOCAL_OVERLAY_FILE = "local.yaml"
    #: yaml 元信息段的 key（所有分层 yaml 通用）
    YAML_META_KEY = "_meta"
    #: yaml 分层合并的基础层名（所有分层 yaml 通用）
    YAML_DEFAULT_LAYER = "default"
    #: local.yaml 里用来指定本机默认环境的字段名（框架约定，不参与业务配置合并）
    #: 双下划线前缀是元字段标记，与业务配置区分开；完整用法见 config/local.yaml 模板注释。
    LOCAL_ENV_KEY = "__env__"

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, env: str = None):
        # 单例第二次及以后调用：仅在显式传了新环境时切换
        if getattr(self, "_initialized", False):
            if env and env != self._env:
                self.switch(env)
            return

        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(self.project_root, "config")

        # 1) 先加载 .env，后续占位符解析才能取到值
        self._load_dotenv()

        # 2) 读取主配置原始内容与元信息
        self._config_path = os.path.join(self.config_dir, self.MAIN_CONFIG_FILE)
        raw = self._read_yaml(self._config_path)
        self._meta: Dict[str, Any] = raw.pop(self.YAML_META_KEY, {}) or {}
        self._raw = raw

        self._available_envs: List[str] = self._meta.get("available_envs") or list(raw.keys())
        default_env = self._meta.get("default_env", "test")

        # 3) 环境优先级：显式传参 > 环境变量 ENV > local.yaml 指定 > 默认环境
        local_overlay = self._read_local_overlay()
        self._env = (
            env
            or os.getenv(self.ENV_VAR)
            or local_overlay.get(self.LOCAL_ENV_KEY)
            or default_env
        )
        if self._env not in self._available_envs:
            raise ValueError(
                f"未知环境 '{self._env}'，可选：{self._available_envs}（用 -e 指定）"
            )

        self._initialized = True
        self.reload()

    # ------------------------------------------------------------------
    # 加载与合并
    # ------------------------------------------------------------------
    def _load_dotenv(self) -> None:
        env_path = os.path.join(self.config_dir, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)

    def _read_yaml(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _read_local_overlay(self) -> Dict[str, Any]:
        """本地个人覆盖层，不入库；LOCAL_ENV_KEY (__env__) 用于指定本机默认环境"""
        local_path = os.path.join(self.config_dir, self.LOCAL_OVERLAY_FILE)
        if os.path.exists(local_path):
            return self._read_yaml(local_path) or {}
        return {}

    def _merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """ 分层合并机制的核心引擎 深合并：override 覆盖 base（嵌套 dict 递归合并）"""
        result = copy.deepcopy(base)
        for key, value in (override or {}).items():
            if key == self.LOCAL_ENV_KEY:
                continue
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _resolve_placeholders(self, data: Any) -> Any:
        """递归把 ${VAR} 替换为环境变量值；取不到时替换为空串并保留原 key 记录"""
        if isinstance(data, dict):
            return {k: self._resolve_placeholders(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._resolve_placeholders(v) for v in data]
        if isinstance(data, str):
            def _replace(match):
                return os.getenv(match.group(1).strip(), "")
            return _VAR_PATTERN.sub(_replace, data)
        return data

    def reload(self) -> None:
        """按当前环境重新合并配置（切换环境后调用）"""
        merged = self._merge(self._raw.get(self.YAML_DEFAULT_LAYER, {}), self._raw.get(self._env, {}))
        merged = self._merge(merged, self._read_local_overlay())
        merged = self._resolve_placeholders(merged)
        merged["env"] = self._env
        self._config = merged
        self._validate()

    def _validate(self) -> None:
        """必填项校验：缺失立刻报错，避免带着残缺配置跑到一半才失败"""
        required = self._meta.get("required_keys") or []
        missing = [k for k in required if not self._config.get(k)]
        if missing:
            raise ValueError(
                f"环境 '{self._env}' 缺少必填配置项 {missing}，"
                f"请检查 config/environments.yaml 或 config/local.yaml"
            )

    # ------------------------------------------------------------------
    # 环境切换
    # ------------------------------------------------------------------
    @property
    def current_env(self) -> str:
        return self._env

    @property
    def available_envs(self) -> List[str]:
        return list(self._available_envs)

    def switch(self, env: str) -> None:
        """运行期切换环境（会重新合并并校验）
        switch 是 EnvManager 的核心动作方法——把
        「校验 → 更新状态 → 重新加载配置 → 校验配置完整性」
        这一连串动作封装在一起，
        保证调用者只需要一行 config.switch("xxx") 
        就能干净地完成环境切换，不会留下半更新状态。"""
        if env not in self._available_envs:
            raise ValueError(f"未知环境 '{env}'，可选：{self._available_envs}")
        self._env = env
        os.environ[self.ENV_VAR] = env
        self.reload()

    # ------------------------------------------------------------------
    # 取值
    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def exists(self, key: str) -> bool:
        return key in self._config

    def get_all(self) -> Dict[str, Any]:
        return copy.deepcopy(self._config)

    def load_layered_yaml(self, filename: str) -> Dict[str, Any]:
        """加载其它同样按环境分层的 yaml（如 database.yaml），返回当前环境的合并结果

        合并规则与主配置一致：default 层 + 当前环境层 + local.yaml 覆盖
        """
        path = filename if os.path.isabs(filename) else os.path.join(self.config_dir, filename)
        raw = self._read_yaml(path)
        raw.pop(self.YAML_META_KEY, None)
        merged = self._merge(raw.get(self.YAML_DEFAULT_LAYER, {}), raw.get(self._env, {}))
        merged = self._merge(merged, self._read_local_overlay())
        return self._resolve_placeholders(merged)

    def describe(self) -> str:
        """给日志/命令行用的环境概览
        典型的"聚合展示"方法——把分散在配置对象里的关键字段，
        收敛成一行可读的"名片"字符串。"""
        return (
            f"环境={self._env} | base_url={self.get('base_url', '-')} | "
            f"browser={self.get('browser', '-')} | headless={self.get('headless', '-')}"
        )


# 全工程统一配置单例
config = EnvManager()