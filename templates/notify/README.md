# 自定义通知模板目录

把内置模板复制到这里即可覆盖默认外观：

```bash
cp ../common/notifier/templates/*.j2 .
```

- 支持的文件：`dingtalk.md.j2`、`email.html.j2`、`email.txt.j2`
- 本目录优先级高于 `common/notifier/templates/`
- 也可以把模板放到任意目录，用环境变量 `NOTIFY_TEMPLATE_DIR` 指定
- 模板缺失或语法错误时会自动降级到内置模板，**不会导致通知发不出去**
- 变量说明与示例见 `docs/通知与模板.md`
