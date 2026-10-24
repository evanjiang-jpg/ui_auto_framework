# -*- coding: utf-8 -*-
"""
模板引擎层

只做两件事：
  1. 定位并加载 Jinja2 模板（三级查找 + 内置兜底）
  2. 把 TestResult 统一转换成模板上下文（所有模板共享同一份数据）

三级查找优先级：
  自定义目录（NOTIFY_TEMPLATE_DIR 或 templates/notify/） > 内置模板目录 > 代码内置字符串
兜底保证：模板被删或写坏时，通知照发，只是外观退化，绝不因此丢通知。
"""
import os
from datetime import datetime
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from common.env_manager import config
from common.logger import get_logger
from common.notifier.models import TestResult

logger = get_logger("notify_templates")


# ----------------------------------------------------------------------
# 内置兜底模板（模板文件缺失/损坏时的最后一道保险）
# ----------------------------------------------------------------------
BUILTIN_TEMPLATES: Dict[str, str] = {
    "dingtalk.md.j2": """## {% if is_success %}✅{% else %}❌{% endif %} UI自动化测试执行通知
- **执行结果**：{{ status_text }}
- **执行环境**：{{ env | upper }}
- **用例总数**：{{ total }}
- **通过 / 失败 / 异常 / 跳过**：{{ passed }} / {{ failed }} / {{ broken }} / {{ skipped }}
- **通过率**：{{ pass_rate }}%
- **总耗时**：{{ duration }}s{% if retried_success %}（重试成功 {{ retried_success }} 次）{% endif %}
{% if report_url %}
[👉 点击查看完整报告]({{ report_url }})
{% endif %}
{% if failed_cases %}
**失败用例（前 {{ failed_cases | length }} 条）**：
{% for case in failed_cases %}
- {{ case.name }}
{% endfor %}
{% endif %}
{% if at_mobiles %}{% for mobile in at_mobiles %}@{{ mobile }} {% endfor %}{% endif %}
{% if at_all %}@所有人{% endif %}
""",
    "email.html.j2": """<html><body style="font-family:Microsoft YaHei,Arial;padding:20px;color:#333">
<h2>UI自动化测试执行报告</h2>
<p>环境：{{ env | upper }} ｜ 通过率：{{ pass_rate }}% ｜ 用例总数：{{ total }}</p>
<p>通过 {{ passed }} / 失败 {{ failed }} / 异常 {{ broken }} / 跳过 {{ skipped }}，耗时 {{ duration }}s</p>
{% if failed_cases %}
<h3 style="color:#ff4d4f">失败用例</h3>
<ul>{% for case in failed_cases %}<li>{{ case.name }} —— {{ case.message }}</li>{% endfor %}</ul>
{% endif %}
{% if report_url %}<p><a href="{{ report_url }}">查看完整报告</a></p>{% endif %}
<p style="color:#999;font-size:12px">本邮件由自动化框架自动发送，执行时间 {{ executed_at }}</p>
</body></html>""",
    "email.txt.j2": """UI自动化测试执行报告
环境：{{ env | upper }} ｜ 通过率：{{ pass_rate }}% ｜ 用例总数：{{ total }}
通过 {{ passed }} / 失败 {{ failed }} / 异常 {{ broken }} / 跳过 {{ skipped }}，耗时 {{ duration }}s
{% if failed_cases %}
失败用例：
{% for case in failed_cases %}{{ loop.index }}. {{ case.name }} —— {{ case.message }}
{% endfor %}{% endif %}
{% if report_url %}报告链接：{{ report_url }}{% endif %}
执行时间：{{ executed_at }}
""",
}


def _template_search_paths() -> list:
    """按优先级返回模板搜索目录列表"""
    builtin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    custom_dir = os.getenv(
        "NOTIFY_TEMPLATE_DIR",
        os.path.join(config.project_root, "templates", "notify"),
    )
    paths = []
    if custom_dir and os.path.isdir(custom_dir):
        paths.append(custom_dir)
    if os.path.isdir(builtin_dir):
        paths.append(builtin_dir)
    return paths


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_template_search_paths()),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    original_get_template = env.get_template

    def get_template_with_fallback(name, *args, **kwargs):
        try:
            return original_get_template(name, *args, **kwargs)
        except TemplateNotFound:
            if name in BUILTIN_TEMPLATES:
                logger.warning(f"模板 {name} 未找到，使用内置兜底模板")
                return env.from_string(BUILTIN_TEMPLATES[name])
            raise

    env.get_template = get_template_with_fallback
    return env


_template_env = _build_env()


def render(template_name: str, ctx: Dict[str, Any], fallback_name: str = "") -> str:
    """渲染模板，任何异常都自动降级到内置兜底模板"""
    try:
        return _template_env.get_template(template_name).render(**ctx).strip()
    except Exception as e:
        logger.error(f"模板 {template_name} 渲染失败，使用内置兜底: {e}")
        key = fallback_name or template_name
        return _template_env.from_string(BUILTIN_TEMPLATES[key]).render(**ctx)


def build_context(result: TestResult) -> Dict[str, Any]:
    """把 TestResult 转换为模板上下文（所有模板共享同一份数据）"""
    failed_cases = []
    for item in result.failed_cases:
        if isinstance(item, (tuple, list)):
            name = item[0]
            msg = item[1] if len(item) > 1 else ""
        else:
            name, msg = str(item), ""
        failed_cases.append({"name": name, "message": msg, "status": "failed"})

    is_success = result.is_success()
    commit_msg = result.commit_msg or ""

    return {
        # ---------- 基础信息 ----------
        "env": result.env,
        "branch": commit_msg.split(" ")[0] if commit_msg else "",
        "author": result.commit_author,
        "commit_msg": commit_msg,
        "pipeline_id": result.pipeline_id,
        "pipeline_url": f"/pipelines/{result.pipeline_id}" if result.pipeline_id else "",
        "trigger_type": "CI" if result.pipeline_id else "manual",
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_time": result.start_time,
        "end_time": result.end_time,
        # ---------- 执行结果 ----------
        "is_success": is_success,
        "status_text": "全部通过" if is_success else "存在失败",
        "total": result.total,
        "passed": result.passed,
        "failed": result.failed,
        "broken": result.error,
        "skipped": result.skipped,
        "retried_success": result.rerun,
        "pass_rate": int(round(result.pass_rate)),
        "duration": round(result.duration_sec, 1),
        # ---------- 失败详情 ----------
        "failed_cases": failed_cases,
        # ---------- 链接 ----------
        "report_url": result.report_url,
        "report_path": result.report_path,
        # ---------- @ 配置 ----------
        "at_mobiles": [x for x in os.getenv("DINGTALK_AT_MOBILES", "").split(",") if x],
        "at_all": os.getenv("DINGTALK_AT_ALL", "false").lower() == "true",
    }
