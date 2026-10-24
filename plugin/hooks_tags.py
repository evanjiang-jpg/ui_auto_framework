# -*- coding: utf-8 -*-
"""
钩子点：数据驱动用例自动打 Allure 标签

解决的问题：数据驱动用例如果每条都手写一堆 @allure.xxx 装饰器，
标签和测试数据分处两地，改数据忘改标签，长期维护必然错位。

做法：用例只写业务逻辑，标签信息写在数据文件里（case_name / priority /
tags / owner / feature / story / description / expected），
本钩子在收集阶段自动读取并转成 Allure 标签，做到「一处维护」。

实现约定（与 allure-pytest 的契约一致，不是自己发明）：
  - 标签类信息统一通过 ``pytest.mark.allure_label(<值>, label_type=<类型>)`` 注入
  - 描述类信息通过 ``pytest.mark.allure_description_html`` 注入
  - severity 的取值必须是 allure 认识的字符串：blocker/critical/normal/minor
"""
import pytest

from common.logger import get_logger

logger = get_logger("hooks_tags")

# 数据文件里的元数据字段（不参与 description 的参数罗列）
_META_FIELDS = (
    "case_name", "priority", "tags", "owner", "feature", "story",
    "description", "expected", "expect_success",
)

# 优先级 -> Allure severity（取值必须为 allure 认识的字符串）
_PRIORITY_MAP = {
    "P0": "blocker",
    "P1": "critical",
    "P2": "normal",
    "P3": "minor",
}


def _add_label(item, label_type: str, *values) -> None:
    """按 allure-pytest 的契约注入标签"""
    values = tuple(v for v in values if v)
    if values:
        item.add_marker(pytest.mark.allure_label(*values, label_type=label_type))


def _extract_case_data(item):
    """从参数化数据里找出那条「用例字典」"""
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return None
    for value in callspec.params.values():
        if isinstance(value, dict) and (
            "case_name" in value or "expected" in value or "priority" in value
        ):
            return value
    return None


def _apply_priority(item, case_data) -> None:
    priority = case_data.get("priority")
    if priority in _PRIORITY_MAP:
        _add_label(item, "severity", _PRIORITY_MAP[priority])


def _apply_tags(item, case_data) -> None:
    tags = case_data.get("tags") or []
    if tags:
        _add_label(item, "tag", *tags)
    owner = case_data.get("owner")
    if owner:
        _add_label(item, "owner", owner)


def _apply_feature_story(item, case_data) -> None:
    default_feature = item.parent.name.replace("test_", "") if item.parent else ""
    feature = case_data.get("feature") or default_feature
    if feature:
        _add_label(item, "feature", feature)
    story = case_data.get("story")
    if story:
        _add_label(item, "story", story)


def _apply_description(item, case_data) -> None:
    """把「用例描述 + 预期结果 + 实际使用的测试数据」写进报告描述"""
    description = case_data.get("description", "")
    expected = case_data.get("expected", "")
    params = "\n".join(
        f"- {k} = {v}" for k, v in case_data.items() if k not in _META_FIELDS
    )

    sections = []
    if description:
        sections.append(description)
    if expected:
        sections.append(f"<b>预期结果</b>：{expected}")
    if params:
        sections.append("<b>测试数据</b>：<br/>" + params.replace("\n", "<br/>"))

    if sections:
        item.add_marker(pytest.mark.allure_description_html("<br/><br/>".join(sections)))


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """收集阶段：把数据文件里的元数据转成 Allure 标签"""
    tagged = 0
    for item in items:
        case_data = _extract_case_data(item)
        if not case_data:
            continue
        _apply_priority(item, case_data)
        _apply_tags(item, case_data)
        _apply_feature_story(item, case_data)
        _apply_description(item, case_data)
        tagged += 1

    if tagged:
        logger.debug(f"数据驱动自动打标签完成，共处理 {tagged} 条用例")
