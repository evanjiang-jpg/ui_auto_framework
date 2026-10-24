# -*- coding: utf-8 -*-
"""
测试数据读取工具：把「测试数据」和「测试代码」彻底分离

能力：
  1. 自动识别 yaml / yml / json，调用时可省略后缀
  2. 支持 global 段公共参数，自动并入每条用例
  3. 支持 ${VAR} 占位符，优先取全局上下文，其次取环境变量
  4. 支持笛卡尔积：列表字段自动组合成多组用例
"""
import os
import re
import json
import itertools
from typing import Any, Dict, List

import yaml

from common.env_manager import config
from common.global_context import context

_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
_SUFFIXES = (".yaml", ".yml", ".json")


def _data_dir() -> str:
    d = os.path.join(config.project_root, "data")
    os.makedirs(d, exist_ok=True)
    return d


def _resolve_vars(data: Any) -> Any:
    """递归解析 ${var}：优先全局上下文，其次环境变量，都没有则原样保留"""
    if isinstance(data, dict):
        return {k: _resolve_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_resolve_vars(item) for item in data]
    if isinstance(data, str) and "${" in data:
        def _replace(match):
            name = match.group(1).strip()
            value = context.get(name)
            if value is None:
                value = os.getenv(name)
            return str(value) if value is not None else match.group(0)
        return _VAR_PATTERN.sub(_replace, data)
    return data


def _generate_combinations(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """列表字段做笛卡尔积，标量字段直接带上"""
    list_fields = {k: v for k, v in params.items() if isinstance(v, list)}
    scalar_fields = {k: v for k, v in params.items() if not isinstance(v, list)}
    if not list_fields:
        return [params]

    combinations = []
    for combo in itertools.product(*list_fields.values()):
        case = scalar_fields.copy()
        case.update(dict(zip(list_fields.keys(), combo)))
        combinations.append(case)
    return combinations


def _locate_file(file_name: str) -> str:
    """定位数据文件，支持省略后缀"""
    data_dir = _data_dir()
    if file_name.endswith(_SUFFIXES):
        path = os.path.join(data_dir, file_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"测试数据文件不存在: {path}")
        return path

    for suffix in _SUFFIXES:
        path = os.path.join(data_dir, file_name + suffix)
        if os.path.exists(path):
            return path
    tried = [file_name + s for s in _SUFFIXES]
    raise FileNotFoundError(f"测试数据文件不存在，已尝试：{tried}")


def load_test_data(file_name: str, auto_combine: bool = False,
                   resolve_vars: bool = True) -> List[Dict[str, Any]]:
    """加载测试数据，返回值可直接传给 pytest.mark.parametrize

    :param file_name:    data 目录下的文件名，可省略后缀
    :param auto_combine: 是否对列表字段做笛卡尔积
    :param resolve_vars: 是否解析 ${var} 占位符
    """
    file_path = _locate_file(file_name)
    suffix = os.path.splitext(file_path)[1].lower()

    with open(file_path, "r", encoding="utf-8") as f:
        if suffix == ".json":
            raw = json.load(f)
        else:
            raw = yaml.safe_load(f)

    # 兼容三种结构：纯列表 / {global, cases} / 需组合的字典
    if isinstance(raw, list):
        cases = raw
    elif isinstance(raw, dict) and "cases" in raw:
        global_params = raw.get("global", {}) or {}
        cases = [{**global_params, **case} for case in raw["cases"]]
    elif isinstance(raw, dict) and auto_combine:
        cases = _generate_combinations(raw)
    else:
        raise ValueError(
            f"测试数据格式错误: {file_path}，"
            f"需为列表、含 cases 字段的对象，或开启 auto_combine 的字典"
        )

    if resolve_vars:
        cases = [_resolve_vars(case) for case in cases]
    return cases


def generate_random_phone() -> str:
    import faker
    """生成随机手机号，动态参数示例"""
    return faker.Faker(locale="zh_CN").phone_number()
