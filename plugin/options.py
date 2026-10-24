# -*- coding: utf-8 -*-
"""
钩子点：命令行参数 + 环境初始化 + 报告头信息

职责单一：只处理"怎么指定环境、怎么把环境信息展示出来"，不做任何业务。
"""
import pytest

from common.env_manager import EnvManager


def pytest_addoption(parser):
    """注册框架自定义命令行参数"""
    group = parser.getgroup("ui-framework", "UI 自动化测试框架参数")

    # 注意：pytest 保留小写短选项（lowercase shortoptions reserved），
    # 因此这里只用长选项 --env；run.py 对外仍提供 -e/--env 供用户使用。
    group.addoption(
        "--env",
        action="store",
        default=None,
        metavar="ENV",
        help="指定测试环境（dev/test/staging/prod），优先级高于环境变量 ENV",
    )
    group.addoption(
        "--api-login",
        action="store_true",
        default=False,
        help="使用接口登录替代 UI 登录（速度提升 3-5 倍）",
    )
    group.addoption(
        "--db-init",
        action="store_true",
        default=False,
        help="执行前重新初始化数据库表结构与种子数据（仅 sqlite demo 用）",
    )


def pytest_configure(config):
    """按命令行指定的环境切换全局配置

    注意：pluggy 要求钩子实现沿用 hookspec 的参数名（这里是 config），
    因此不能重命名参数，只能在函数体内做局部导入。
    """
    env = config.getoption("env")
    if env:
        from common.env_manager import EnvManager
        EnvManager(env)


def pytest_report_header(config):
    """在 pytest 报告头部展示当前环境概览，方便确认跑的是哪个环境"""
    from common.env_manager import EnvManager
    return [f"UI框架配置 -> {EnvManager().describe()}"]
