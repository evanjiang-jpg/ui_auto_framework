# -*- coding: utf-8 -*-
"""邮件通道：HTML + 纯文本双模板，自动把 Allure 报告打包为附件"""
import os
import ssl
import shutil
import smtplib
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from typing import List, Optional

from common.logger import get_logger
from common.notifier.models import TestResult
from common.notifier import templates

logger = get_logger("notify_email")


def _pack_report(report_dir: str) -> str:
    """把 Allure 报告目录打成 zip，返回 zip 路径"""
    fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="allure_report_")
    os.close(fd)
    base = zip_path[:-4]
    shutil.make_archive(base, "zip", report_dir)
    return f"{base}.zip"


def _attach_file(msg: MIMEMultipart, file_path: str) -> None:
    with open(file_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    filename = os.path.basename(file_path)
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=("utf-8", "", filename),
    )
    msg.attach(part)


def send_email(
    result: TestResult,
    smtp_host: str,
    smtp_port: int,
    use_ssl: bool,
    user: str,
    password: str,
    sender: str,
    receivers: List[str],
    cc: Optional[List[str]] = None,
    attach_report_dir: str = "",
    timeout: int = 15,
) -> bool:
    """发送 HTML 测试报告邮件（纯文本作为兼容副本，报告 zip 作为附件）"""
    if not receivers:
        logger.warning("未配置收件人，跳过邮件通知")
        return False

    ctx = templates.build_context(result)
    html_body = templates.render("email.html.j2", ctx, fallback_name="email.html.j2")
    txt_body = templates.render("email.txt.j2", ctx, fallback_name="email.txt.j2")

    msg = MIMEMultipart("mixed")
    subject = f"【{ctx['env'].upper()}】UI自动化测试报告 - {ctx['status_text']}（通过率 {ctx['pass_rate']}%）"
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender or user
    msg["To"] = ", ".join(receivers)
    if cc:
        msg["Cc"] = ", ".join(cc)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(txt_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    # 附件：Allure 报告 zip（超过 20MB 不附加，避免被邮件服务拒收）
    zip_path = ""
    if attach_report_dir and os.path.isdir(attach_report_dir):
        try:
            zip_path = _pack_report(attach_report_dir)
            if os.path.getsize(zip_path) <= 20 * 1024 * 1024:
                _attach_file(msg, zip_path)
                logger.info(f"已附加 Allure 报告: {os.path.basename(zip_path)}")
            else:
                logger.warning("报告 zip 超过 20MB，跳过附加")
        except Exception as e:
            logger.warning(f"打包报告失败，跳过附件: {e}")

    all_recipients = list(receivers) + list(cc or [])
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)
            server.starttls()
        server.login(user, password)
        server.sendmail(sender or user, all_recipients, msg.as_string())
        server.quit()
        logger.info(f"邮件通知发送成功，收件人: {all_recipients}")
        return True
    except Exception as e:
        logger.error(f"邮件通知发送异常: {e}")
        return False
    finally:
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass
