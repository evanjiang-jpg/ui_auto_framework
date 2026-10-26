# -*- coding: utf-8 -*-
"""
pytest 根配置 —— 只做「装配」，不承载任何业务逻辑

原先各种 fixture、hook 混在本文件里，越加越乱；现在全部下沉到 plugin/ 包，
按钩子点分文件维护，本文件只声明加载哪些插件。

各插件职责：
    plugin.options          —— 命令行参数、环境切换、报告头信息
    plugin.fixtures         —— 全部 fixture（上下文/浏览器/登录态/接口前置/数据库）
    plugin.hooks_tags       —— 数据驱动自动打 Allure 标签
    plugin.hooks_screenshot —— 失败自动截图（重试时不重复截）
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 强制把工作目录切到项目根：
#   pytest.ini 的 addopts 里 --alluredir=allure-results 是相对路径，
#   若用户在 testcases/ 等子目录下跑 pytest，会错误地把报告输出到子目录。
#   这里在 conftest 模块加载最早期就 chdir，确保后续所有相对路径都以项目根为基准。
os.chdir(ROOT_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

pytest_plugins = [
    "plugin.options",
    "plugin.fixtures",
    "plugin.hooks_tags",
    "plugin.hooks_screenshot",
]