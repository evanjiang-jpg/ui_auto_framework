# -*- coding: utf-8 -*-
"""
通知数据模型 + 结果解析

只负责「把一次测试执行的结果整理成结构化数据」，不涉及任何发送动作。
结果来源为 allure-results/*-result.json —— 不依赖 pytest 内部 hook，
因此本地、GitLab、Jenkins、GitHub Actions 上表现完全一致。
"""
import os
import json
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from common.logger import get_logger

logger = get_logger("notify_models")


@dataclass
class TestResult:
    """一次测试执行的汇总结果"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    rerun: int = 0
    duration_sec: float = 0.0
    pass_rate: float = 0.0

    env: str = "test"
    start_time: str = ""
    end_time: str = ""

    failed_cases: List[Tuple[str, str]] = field(default_factory=list)

    report_url: str = ""
    report_path: str = ""

    commit_author: str = ""
    commit_msg: str = ""
    pipeline_id: str = ""

    def is_success(self) -> bool:
        return self.failed == 0 and self.error == 0


def parse_allure_results(allure_results_dir: str) -> TestResult:
    """从 allure-results 目录解析用例执行结果

    - 跳过 rerun 产生的中间结果，避免重复统计
    - 只保留前 20 条失败用例，防止消息过长被平台截断
    """
    result = TestResult()
    if not os.path.exists(allure_results_dir):
        logger.warning(f"allure-results 目录不存在: {allure_results_dir}")
        return result

    total = passed = failed = error = skipped = rerun = 0
    failed_cases: List[Tuple[str, str]] = []
    duration_ms = 0.0

    for fname in os.listdir(allure_results_dir):
        if not fname.endswith("-result.json"):
            continue
        fpath = os.path.join(allure_results_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # rerun 的中间结果不计入总数
        if data.get("rerunOf") and data.get("retriesCount"):
            rerun += 1
            continue

        status = data.get("status", "")
        name = data.get("name", fname)
        message = ((data.get("statusDetails") or {}).get("message") or "").strip()

        total += 1
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
            failed_cases.append((name, message))
        elif status == "broken":
            error += 1
            failed_cases.append((name, message))
        elif status == "skipped":
            skipped += 1

        duration_ms += (data.get("time") or {}).get("duration", 0)

    result.total = total
    result.passed = passed
    result.failed = failed
    result.error = error
    result.skipped = skipped
    result.rerun = rerun
    result.duration_sec = round(duration_ms / 1000.0, 2)
    result.pass_rate = round(passed / total * 100, 2) if total else 0.0
    result.failed_cases = failed_cases[:20]
    return result
