# -*- coding: utf-8 -*-
"""
通知模板本地预览（不发送真实通知）

用途：调整钉钉/邮件模板样式时，不必真的发一条通知，直接看渲染结果。
用法：
    python scripts/preview_notify.py
    python scripts/preview_notify.py --results allure-results   # 用真实执行结果渲染
"""
import os
import sys
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.notifier import TestResult, parse_allure_results  # noqa: E402
from common.notifier import templates  # noqa: E402


def fake_result() -> TestResult:
    """构造一份假结果，用于预览模板样式"""
    result = TestResult()
    result.total = 42
    result.passed = 39
    result.failed = 3
    result.error = 0
    result.skipped = 0
    result.rerun = 1
    result.duration_sec = 186.5
    result.pass_rate = 92.86
    result.env = "test"
    result.report_url = "https://ci.example.com/job/ui-test/123/allure"
    result.pipeline_id = "1234"
    result.commit_author = "张三"
    result.commit_msg = "feat: 新增订单批量查询功能"
    result.failed_cases = [
        ("TestOrder::test_order_list_with_session_auth", "AssertionError: token 为空"),
        ("TestLogin::test_login_boundary[手机号长度不足11位]", "ValueError: 账号长度不足 11 位"),
        ("TestDbAssertDemo::test_wait_for_row", "DBAssertionError: 等待超时 5s：表 users 中始终没有满足 {'username': 'async_xxx'} 的记录"),
    ]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="通知模板本地预览")
    parser.add_argument("--results", default="",
                        help="allure-results 目录；不传则使用假数据")
    args = parser.parse_args()

    if args.results and os.path.isdir(args.results):
        result = parse_allure_results(args.results)
        print(f"[使用真实结果] 总数={result.total} 通过={result.passed} 失败={result.failed}")
    else:
        result = fake_result()
        print("[使用假数据] 传 --results 可用真实执行结果渲染")

    ctx = templates.build_context(result)

    print("\n" + "=" * 78)
    print("钉钉 Markdown（dingtalk.md.j2）")
    print("=" * 78)
    print(templates.render("dingtalk.md.j2", ctx))

    print("\n" + "=" * 78)
    print("邮件纯文本（email.txt.j2）")
    print("=" * 78)
    print(templates.render("email.txt.j2", ctx))

    html = templates.render("email.html.j2", ctx, fallback_name="email.html.j2")
    out_path = os.path.join(ROOT_DIR, "docs", "preview_email.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("\n" + "=" * 78)
    print(f"邮件 HTML（email.html.j2）已写入: {out_path}")
    print("用浏览器打开该文件即可查看最终样式")
    print("=" * 78)


if __name__ == "__main__":
    main()
