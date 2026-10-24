# -*- coding: utf-8 -*-
"""
统一日志工具：控制台 + 文件双通道

对外提供两个入口，避免使用者踩"导错名字"的坑：
  - get_logger(name)  : 按模块名获取独立 logger（推荐）
  - logger            : 框架默认 logger，供不想传名字的模块直接用
"""
import os
import logging
from datetime import datetime

from common.env_manager import config

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_DIR = os.path.join(config.project_root, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str = "ui_test") -> logging.Logger:
    """获取 logger：同名返回同一实例，重复调用不会叠加 handler"""
    log = logging.getLogger(name)
    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)
    log.propagate = False

    # 控制台：级别由配置 log_level 控制
    level_name = str(config.get("log_level", "INFO")).upper()
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level_name, logging.INFO))
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # 文件：固定 DEBUG，便于事后排查
    log_file = os.path.join(LOG_DIR, f"ui_test_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    log.addHandler(console_handler)
    log.addHandler(file_handler)
    return log


# 框架默认 logger
logger = get_logger("ui_test")
