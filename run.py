#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一执行入口

把「环境切换 + 用例筛选 + 并行 + 重试 + Allure 报告 + 通知」收敛成一个命令，
让本地开发和 CI 流水线使用完全一致的入口，避免「本地能跑、流水线跑不通」。

好处：
run.py 只管自己关心的参数
用户仍可直接传 pytest 原生参数，如 --collect-only、--tb=long、-v 等
常用示例：
    python run.py                                  # test 环境全量，跑完生成并打开报告
    python run.py -e dev -m smoke -n 4             # dev 环境冒烟，4 进程并行
    python run.py -k order -x                      # 只跑名字含 order 的用例，失败即停
    python run.py -m "p0 and not slow" --reruns 2  # 高优用例，失败重跑 2 次
    python run.py --api-login -m smoke             # 用接口登录替代 UI 登录（更快）
    python run.py --no-report --notify             # CI：不出报告、发钉钉/邮件
    python run.py --list-envs                      # 查看可选环境
    python run.py --list-markers                   # 查看全部标签
"""
import os
import sys
import argparse
import shutil
import subprocess
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

"""
构建一个功能完备的命令行参数解析器，定义 python run.py 接受的所有命令行参数。
"""
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="UI 自动化测试统一执行入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ---------- 执行范围 ----------
    group_target = parser.add_argument_group("执行范围")
    group_target.add_argument("-e", "--env", default=None,
                              help="测试环境（dev/test/staging/prod）")
    group_target.add_argument("-m", "--marker", default=None,
                              help="按标签筛选，如 smoke / 'p0 and not slow'")
    group_target.add_argument("-k", "--keyword", default=None,
                              help="按用例名关键字筛选")
    group_target.add_argument("-f", "--file", default="testcases",
                              help="指定用例目录或文件（默认 testcases）")

    # ---------- 执行方式 ----------
    group_run = parser.add_argument_group("执行方式")
    group_run.add_argument("-n", "--workers", type=int, default=None,
                           help="并行进程数（依赖 pytest-xdist）")
    group_run.add_argument("--reruns", type=int, default=None,
                           help="失败重跑次数（依赖 pytest-rerunfailures）")
    group_run.add_argument("--reruns-delay", type=int, default=1,
                           help="重跑前等待秒数（默认 1）")
    group_run.add_argument("-x", "--exitfirst", action="store_true",
                           help="首个失败即停止")
    group_run.add_argument("--api-login", action="store_true",
                           help="用接口登录替代 UI 登录")
    group_run.add_argument("--testmon", action="store_true",
                           help="增量执行：只跑受代码改动影响的用例")
    group_run.add_argument("-s", "--show-output", action="store_true",
                           help="打开输出捕获，显示用例内 print（调试用）")

    # ---------- 报告与清理 ----------
    group_report = parser.add_argument_group("报告与清理")
    group_report.add_argument("--results-dir", default="allure-results",
                              help="Allure 原始结果目录（默认 allure-results）")
    group_report.add_argument("--report-dir", default="allure-report",
                              help="Allure HTML 报告目录（默认 allure-report）")
    group_report.add_argument("--no-report", action="store_true",
                              help="不生成、不打开 HTML 报告（CI 常用）")
    group_report.add_argument("--clean", action="store_true",
                              help="执行前清理历史结果与报告")
    group_report.add_argument("--notify", action="store_true",
                              help="执行后发送钉钉/邮件通知")

    # ---------- 辅助 ----------
    group_help = parser.add_argument_group("辅助")
    group_help.add_argument("--list-envs", action="store_true",
                            help="列出全部可用环境后退出")
    group_help.add_argument("--list-markers", action="store_true",
                            help="列出全部用例标签后退出")

    return parser


# ======================================================================
# 辅助动作
# ======================================================================
def list_envs() -> None:
    from common.env_manager import EnvManager
    mgr = EnvManager()
    print("可用环境：")
    for env in mgr.available_envs:
        mark = "（当前）" if env == mgr.current_env else ""
        print(f"  - {env}{mark}")


def list_markers() -> None:
    print("用例标签（注册于 pytest.ini）：")
    print("  执行层级：smoke / p0 / p1 / p2")
    print("  业务模块：login / order / user / payment / search")
    print("  用例类型：ui / api / db / regression")
    print("  执行特征：slow / flaky / skip_ci")
    print("\n组合示例：python run.py -m \"smoke and not slow\"")


def clean_artifacts(results_dir: str, report_dir: str) -> None:
    for d in (results_dir, report_dir):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"  已清理: {d}")


# ======================================================================
# 组装 pytest 命令
# ======================================================================
def build_pytest_cmd(args, extra_args) -> list:
    cmd = [sys.executable, "-m", "pytest"]

    if args.env:
        cmd += ["--env", args.env]
    if args.marker:
        cmd += ["-m", args.marker]
    elif args.no_report:
        # CI 模式（不出报告）默认排除需要真人介入的用例，避免流水线被卡
        cmd += ["-m", "not skip_ci"]
    if args.keyword:
        cmd += ["-k", args.keyword]
    if args.workers:
        cmd += ["-n", str(args.workers)]
    if args.reruns is not None:
        cmd += ["--reruns", str(args.reruns),
                "--reruns-delay", str(args.reruns_delay)]
    if args.exitfirst:
        cmd += ["-x"]
    if args.api_login:
        cmd += ["--api-login"]
    if args.testmon:
        cmd += ["--testmon"]
    if args.show_output:
        cmd += ["-s"]
    if args.results_dir != "allure-results":
        cmd += [f"--alluredir={args.results_dir}"]

    cmd += [args.file]
    cmd += list(extra_args or [])
    return cmd


# ======================================================================
# 报告与通知
# ======================================================================
def generate_report(results_dir: str, report_dir: str):
    """生成 Allure HTML 报告（静态文件），返回 index.html 路径"""
    allure_bin = shutil.which("allure")
    if not allure_bin:
        print("  [跳过] 未检测到 allure 命令行，无法生成 HTML 报告。")
        print("         安装方式：npm i -g allure-commandline（需 Java 环境）")
        print(f"         原始结果仍保留在: {os.path.abspath(results_dir)}")
        return None

    abs_report_dir = os.path.abspath(report_dir)
    proc = subprocess.run(
        [allure_bin, "generate", results_dir, "-o", abs_report_dir, "--clean"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"  [失败] 报告生成失败: {proc.stderr.strip()[:300]}")
        return None
    return os.path.abspath(os.path.join(report_dir, "index.html"))


def serve_report(results_dir: str) -> bool:
    """启动 allure 自带 server，阻塞运行直到手动停止"""
    allure_bin = shutil.which("allure")
    if not allure_bin:
        return False

    print("  按 Ctrl+C 停止报告服务")
    try:
        subprocess.run([allure_bin, "serve", results_dir])
    except KeyboardInterrupt:
        print("\n  报告服务已停止")
    return True


def send_notification(results_dir: str, report_path: str) -> None:
    from common.notifier import TestNotifier, parse_allure_results
    from common.env_manager import config

    result = parse_allure_results(results_dir)
    result.env = config.current_env
    result.report_url = os.getenv("CI_BUILD_URL", "") or (report_path or "")
    result.commit_author = os.getenv("CI_COMMIT_AUTHOR", "")
    result.commit_msg = os.getenv("CI_COMMIT_MSG", "")
    result.pipeline_id = os.getenv("CI_PIPELINE_ID", "")

    TestNotifier().send(result)


# ======================================================================
# 主流程
# ======================================================================
def main() -> None:
    parser = build_parser()
    """extra_args 的透传
    用户输入: python run.py -m smoke -v --tb=long
    run.py 认识的: -m smoke → 进 args
    不认识的:      -v --tb=long → 进 extra_args，透传给 pytest
    """
    args, extra_args = parser.parse_known_args()

    if args.list_envs:
        list_envs()
        return
    if args.list_markers:
        list_markers()
        return

    # 先设置环境变量，保证后续导入的配置读到正确环境
    if args.env:
        os.environ["ENV"] = args.env

    from common.logger import logger
    from common.env_manager import config
    from common.notifier import parse_allure_results

    results_dir = args.results_dir
    report_dir = args.report_dir

    print("=" * 78)
    print(f"  UI 自动化测试  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {config.describe()}")
    print(f"  用例目录: {args.file}")
    print("=" * 78)

    if args.clean:
        print("执行前清理：")
        clean_artifacts(results_dir, report_dir)

    cmd = build_pytest_cmd(args, extra_args)
    logger.debug(f"pytest 命令: {' '.join(cmd)}")
    """subprocess.call 是阻塞的——主进程会一直等 pytest 跑完，拿到退出码才继续往下走。"""
    print(f"\n>>> 开始执行: {' '.join(cmd[2:])}\n")
    exit_code = subprocess.call(cmd, cwd=ROOT_DIR)

    # ---------- 汇总 ----------
    result = parse_allure_results(results_dir)
    print("\n" + "=" * 78)
    print(f"  执行汇总  |  环境 {config.current_env.upper()}")
    print(f"  总数: {result.total}  通过: {result.passed}  失败: {result.failed}  "
          f"异常: {result.error}  跳过: {result.skipped}  通过率: {result.pass_rate}%")
    print("=" * 78)

    # ---------- 报告 ----------
    report_path = None
    if not args.no_report:
        print("\n生成 Allure 报告...")
        report_path = generate_report(results_dir, report_dir)
        if report_path:
            print(f"  ✅ 静态报告已生成: {report_path}")
            print("\n启动 Allure 报告服务（allure serve）...")
            serve_report(results_dir)
            print("\n如需直接打开静态报告：")
            print(f"  python -m http.server 8080 --directory {os.path.abspath(report_dir)}")
    else:
        print("\n[CI 模式] 已跳过 HTML 报告生成与打开")

    # ---------- 通知 ----------
    if args.notify:
        print("\n发送通知...")
        try:
            send_notification(results_dir, report_path)
        except Exception as e:
            logger.error(f"通知发送失败（不影响用例结果）: {e}")

    # ---------- 结果 ----------
    if exit_code == 0 and result.is_success():
        print("\n✅ 全部用例通过")
    else:
        print(f"\n❌ 存在失败用例（pytest 退出码 {exit_code}）")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()