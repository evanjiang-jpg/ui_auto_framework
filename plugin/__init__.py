# -*- coding: utf-8 -*-
"""
pytest 插件包

把原先堆在 conftest.py 里的各种能力按「钩子点」拆分为独立模块，
conftest.py 只负责声明加载哪些插件，不再承载任何业务逻辑：

    options          : 命令行参数 + 环境初始化
    fixtures         : 所有 fixture（上下文 / 浏览器 / 登录态 / 接口前置 / 数据库）
    hooks_tags       : 数据驱动自动打 Allure 标签
    hooks_screenshot : 用例失败自动截图（含重试不重复截图）
"""
