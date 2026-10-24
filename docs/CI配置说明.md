# CI 配置说明

> 本文档详细列出 GitHub Actions 流水线所需的全部 Secrets 配置，
> 包含每个变量的含义、取值来源、获取步骤。

---

## 一、总览

```
本地开发用 config/.env          (从 config/.env.example 复制)
CI 流水线用 GitHub Secrets       (Settings → Secrets and variables → Actions)

两者字段名完全一致，代码里通过 os.getenv() 统一读取，不需要改业务代码。
```

---

## 二、GitHub Secrets 配置入口

```
仓库页面 → Settings → Secrets and variables → Actions → New repository secret
直接打开：https://github.com/evanjiang-jpg/ui_auto_framework/settings/secrets/actions
```

---

## 三、钉钉通知（推荐优先启用）

### 3.1 需要配置的 Secrets

| Secret Name | 必填 | 取值 | 说明 |
|-------------|------|------|------|
| `DINGTALK_ENABLED` | ✅ 是 | `true` | 开启钉钉通知通道；想关闭改 `false` 或删除 |
| `DINGTALK_WEBHOOK` | ✅ 是 | `https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxx` | 钉钉自定义机器人的 webhook 地址 |
| `DINGTALK_SECRET` | ⚠️ 条件必填 | `SECxxxxxxxxxxxxxxxxxxxxxxxxxx` | 机器人安全设置选"加签"时必填；用"自定义关键词"方式则不需要 |

### 3.2 钉钉机器人创建步骤

```
① 打开一个钉钉群（测试专用，别用工作群）
② 群聊右上角 ⋯ → 群设置 → 智能群助手 → 添加机器人
③ 选择 "自定义"
④ 机器人名字填：自动化测试（或随你喜欢）
⑤ 安全设置（三选一，推荐前两种）：

   方式 A：自定义关键词（最简单，推荐）
     → 关键词填：自动化测试
     → 不需要配 DINGTALK_SECRET

   方式 B：加签（更安全）
     → 安全设置选 "加签"
     → 记录下密钥（以 SEC 开头的一串）
     → 密钥填到 GitHub Secret DINGTALK_SECRET

   方式 C：IP 白名单
     → GitHub Actions 出口 IP 经常变，不推荐

⑥ 创建完成后复制 webhook 地址
⑦ 把 webhook 地址填到 GitHub Secret DINGTALK_WEBHOOK
```

### 3.3 手动测试 webhook 通不通（可选）

PowerShell 里直接调用 webhook 验证：

```powershell
$body = @{
    msgtype = "text"
    text = @{ content = "自动化测试 手动测试消息" }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "你的DINGTALK_WEBHOOK值" -Method Post -ContentType "application/json" -Body $body
```

返回 `{"errcode":0,"errmsg":"ok"}` 或钉钉群里收到消息 → webhook 没问题。

---

## 四、邮件通知（可选）

### 4.1 需要配置的 Secrets

| Secret Name | 必填 | 取值 | 说明 |
|-------------|------|------|------|
| `EMAIL_ENABLED` | ✅ 是 | `false` | 默认关闭；想启用改 `true` |
| `EMAIL_SMTP_HOST` | ✅ 开启后必填 | `smtp.qq.com` / `smtp.163.com` / `smtp.exmail.qq.com` | SMTP 服务器地址 |
| `EMAIL_SMTP_PORT` | 否 | `465`（默认） | SMTP 端口，QQ/163 都是 465 |
| `EMAIL_USER` | ✅ 开启后必填 | `yourname@qq.com` | 发件邮箱地址 |
| `EMAIL_PASSWORD` | ✅ 开启后必填 | **授权码**（不是登录密码！） | 见下方 4.2 获取方式 |
| `EMAIL_RECEIVERS` | ✅ 开启后必填 | `tester@example.com` 或 `a@qq.com,b@qq.com` | 收件人，多个用英文逗号分隔 |
| `EMAIL_CC` | 否 | `leader@example.com` | 抄送人，多个用英文逗号分隔 |

### 4.2 QQ 邮箱授权码获取（最常用）

```
① 网页登录 QQ 邮箱 https://mail.qq.com
② 顶部 "设置" → "账号"
③ 找到 POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
④ 开启 "POP3/SMTP服务" 和 "IMAP/SMTP服务"
⑤ 按提示发短信验证
⑥ 验证通过后显示一串 16 位授权码 ← 复制这个
⑦ 把授权码填到 GitHub Secret EMAIL_PASSWORD（注意：是授权码，不是 QQ 登录密码）
```

### 4.3 常见邮箱 SMTP 参数

| 邮箱 | SMTP Host | Port |
|------|-----------|------|
| QQ 邮箱 | `smtp.qq.com` | 465 |
| 163 邮箱 | `smtp.163.com` | 465 |
| 企业邮箱（腾讯） | `smtp.exmail.qq.com` | 465 |
| Gmail | `smtp.gmail.com` | 465 |

---

## 五、CI 内置变量（不需要手动配置）

workflow 文件 `.github/workflows/ui-test.yml` 里有一些变量**GitHub 自动注入**，你不用管：

| 变量 | workflow 里的写法 | 说明 |
|------|------------------|------|
| `CI_PIPELINE_ID` | `${{ github.run_id }}` | 流水线运行 ID |
| `CI_COMMIT_AUTHOR` | `${{ github.actor }}` | 触发者的 GitHub 用户名 |
| `CI_COMMIT_MSG` | `${{ github.event.head_commit.message }}` | 本次 commit 的 message |
| `CI_BUILD_URL` | `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` | 流水线运行结果页面链接 |

通知模板里会用到这些，让接收通知的人能点进流水线页面看详情。

---

## 六、完整配置检查清单

配完 Secrets 后确认列表：

- [ ] `DINGTALK_ENABLED` = `true`
- [ ] `DINGTALK_WEBHOOK` = 钉钉机器人 webhook 地址
- [ ] `DINGTALK_SECRET`（如果用加签方式）
- [ ] `EMAIL_ENABLED` = `false`（先关掉，需要时再开）
- [ ] 钉钉机器人关键词已配置 "自动化测试"

---

## 七、本地 .env 快速配置（开发调试用）

CI 上的配置是 GitHub Secrets，本地跑测试用 `config/.env`：

```powershell
# 1. 从模板复制
Copy-Item config\.env.example config\.env

# 2. 打开 config\.env 填上敏感值
```

`.env` 文件内容示例：

```
# ---------- 钉钉 ----------
DINGTALK_ENABLED=true
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=你的token
DINGTALK_SECRET=

# ---------- 邮件 ----------
EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.qq.com
EMAIL_SMTP_PORT=465
EMAIL_SMTP_SSL=true
EMAIL_USER=yourname@qq.com
EMAIL_PASSWORD=授权码
EMAIL_SENDER=yourname@qq.com
EMAIL_RECEIVERS=tester@example.com
EMAIL_CC=

# ---------- CI ----------
CI_PIPELINE_ID=
CI_COMMIT_AUTHOR=
CI_COMMIT_MSG=
CI_BUILD_URL=
```

> ⚠️ `.env` 文件在 `.gitignore` 里，**不会被提交到 Git**，放心填真实值。

---

## 八、触发 CI 并验证

### 方式 A：手动触发（推荐，不用改代码）

```
仓库页面 → Actions → 左栏 "UI 自动化测试" → 右栏 "Run workflow" 下拉按钮
→ 输入执行范围（默认 p0 or p1）→ 点绿色 "Run workflow"
→ 等跑完（测试用无头浏览器，大概 1-2 分钟）
→ Actions 页面能看到日志，钉钉/邮箱应该能收到通知
```

### 方式 B：push 触发

```powershell
git commit --allow-empty -m "触发 CI 测试"
git push
```

空 commit 也能触发 push 事件的 workflow。

---

## 九、通知没收到？排查清单

### 9.1 CI 有没有跑？

打开 Actions 页面看最新记录：
👉 https://github.com/evanjiang-jpg/ui_auto_framework/actions

**没记录** → push 的分支不是 main/master，或者 workflow 没生效。

**有记录但红色失败** → 点开看日志，先解决测试本身的问题。

### 9.2 日志里有没有通知相关输出？

点开 "执行测试" step，滚到底部：

| 看到 | 含义 |
|------|------|
| `未启用任何通知通道，跳过通知` | `DINGTALK_ENABLED` 或 `EMAIL_ENABLED` 没设为 `true` |
| `钉钉通知已发送` 但群里没收到 | 钉钉机器人关键词/加签没配对 |
| `钉钉通知异常: xxx` | webhook 地址不对，或钉钉返回了错误码 |
| 根本没看到通知相关输出 | workflow 里没传 `--notify`，或者通知 try-except 被静默吞了 |

### 9.3 钉钉机器人关键词

通知模板第一行是：

```
## ✅/❌ UI自动化测试执行通知
```

钉钉机器人关键词必须命中 **"自动化测试"** 或 **"UI"** 或 **"测试执行"**。没配关键词 → webhook 发出去钉钉静默拒绝 → 收不到。

### 9.4 Secret 值有没有空格？

复制粘贴 webhook 地址时容易带上前后空格。确保 Secret 的值**前后没有多余空格和换行**。

### 9.5 `_to_bool` 的坑

Python 的 `_to_bool` 只认**小写** `"true"`：

```python
def _to_bool(name: str, default: bool = False) -> bool:
    return (os.getenv(name, str(default)).lower() == "true")
```

`"TRUE"`、`"True"`、`"1"` 都会返回 `False`。GitHub Secret 里直接填小写 `true`。

---

## 十、常见问题 FAQ

### Q: 修改 Secrets 后需要重新 push 吗？

**不需要**。每次 workflow 运行时 GitHub 都会读取最新的 Secrets。改完直接点 Run workflow 就行。

### Q: 为什么我的 Secret 在 workflow 日志里看不到？

GitHub 会自动把 Secrets 打码（显示为 `***`），这是正常的，防止泄露。

### Q: 想加新的 Secrets，需要改代码吗？

**不需要**。只要 Secret 名和 `.env.example` / `notifier.py` 里的 `os.getenv()` 一致，代码自动能读到。

### Q: 多个仓库都想用同一套通知 Secrets？

用 **Organization Secrets**：组织级别配置一次，所有仓库共享。Settings → Secrets and variables → Actions → Organization secrets。

### Q: 本地跑用 `python run.py --notify` 也能发通知吗？

**能**。只要 `config/.env` 里配了对应的值，本地一样会走通知流程。开发调试时可以用自己的测试机器人验证。