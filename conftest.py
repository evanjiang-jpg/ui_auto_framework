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

# 把工程根加入搜索路径，保证 pytest 以任意方式启动都能正确定位包
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

pytest_plugins = [
    "plugin.options",
    "plugin.fixtures",
    "plugin.hooks_tags",
    "plugin.hooks_screenshot",
]
