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

## 五、飞书通知（可选）

### 5.1 需要配置的 Secrets

| Secret Name | 必填 | 取值 | 说明 |
|-------------|------|------|------|
| `FEISHU_WEBHOOK` | ✅ 启用后必填 | `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxx` | 飞书自定义机器人的 webhook 地址 |
| `FEISHU_SECRET` | ⚠️ 条件必填 | `xxxxxxxxxxxxxxxxxxxxxxxxxx` | 机器人安全设置选"加签"时必填；用"自定义关键词"方式则不需要 |
| `FEISHU_AT_EMAILS` | 否 | `a@example.com,b@example.com` | 需要 @ 的飞书用户邮箱，多个用英文逗号分隔 |
| `FEISHU_AT_ALL` | 否 | `true` | 是否 @所有人 |

> 💡 **不需要手动配 `FEISHU_ENABLED`**。代码自动推断：有 `FEISHU_WEBHOOK` 值就自动开启。

### 5.2 飞书机器人创建步骤

```
① 打开一个飞书群（测试专用，别用工作群）
② 群设置 → 群机器人 → 添加机器人 → 自定义机器人
③ 机器人名字填：自动化测试（或随你喜欢）
④ 安全设置（三选一，推荐前两种）：

   方式 A：自定义关键词（最简单，推荐）
     → 关键词填：自动化测试
     → 不需要配 FEISHU_SECRET

   方式 B：加签（更安全）
     → 安全设置选 "加签"
     → 记录下密钥（一串随机字符串）
     → 密钥填到 GitHub Secret FEISHU_SECRET

   方式 C：IP 白名单
     → GitHub Actions 出口 IP 经常变，不推荐

⑤ 创建完成后复制 webhook 地址
⑥ 把 webhook 地址填到 GitHub Secret FEISHU_WEBHOOK
```

### 5.3 手动测试 webhook 通不通（可选）

PowerShell 里直接调用：

```powershell
$body = @{
    msg_type = "text"
    content = @{ text = "自动化测试 手动测试消息" }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "你的FEISHU_WEBHOOK值" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

返回 `{"StatusCode":0,"StatusMessage":"success"}` 或飞书群里收到消息 → webhook 没问题。

### 5.4 飞书卡片消息效果

```
┌─────────────────────────────────────────────┐
│ ✅ UI自动化测试执行报告            [绿色/红色]│  ← header（成功绿/失败红）
│ 全部通过 ｜ 环境 TEST ｜ 2026-10-24 10:48    │  ← 副标题 + 分割线
├─────────────────────────────────────────────┤
│ ┌────┬────┬────┬────┬────┐                  │
│ │总数│通过│失败│异常│跳过│                  │
│ │ 17 │ 17 │ 0  │ 0  │ 0  │  ← 5 个大数字并排│
│ └────┴────┴────┴────┴────┘                  │
│                                             │
│ 通过率: 100% ｜ 总耗时: 12.3s               │
│                                             │
│ [📊 查看完整 Allure 报告]  [🔗 查看流水线]  │  ← 两个按钮
│                                             │
│ 失败用例：                                   │  ← 有失败才显示
│ - test_login: 元素找不到登录按钮             │
│                                             │
│ 流水线 #40087327052 ｜ 提交人: evanjiang-jpg│  ← 底部注脚
│ feat: add feishu notifier...                │
└─────────────────────────────────────────────┘
```

---

## 六、Allure 报告与 GitHub Pages（可选但推荐）

### 6.1 效果

CI 跑完后自动生成 Allure HTML 报告，部署到 GitHub Pages：

```
通知里的按钮点击 → https://evanjiang-jpg.github.io/ui_auto_framework/
                                 ↑
                           这里直接能看 Allure 报告
（包含图表、用例详情、失败截图、重试历史等）
```

### 6.2 前提条件

| 条件 | 状态 |
|------|------|
| 仓库是 **Public** | ✅ 免费，直接用 |
| 仓库是 **Private** | ✅ 现在也免费了（GitHub Free 已支持） |
| 不需要买域名 | ✅ 用 GitHub 默认的 `xxx.github.io/仓库名` 就行 |

### 6.3 开启 GitHub Pages（一次性操作）

```
① 仓库页面 → Settings（不是 Settings → Secrets，是仓库本身的 Settings）
② 左栏往下拉找到 "Pages"
③ Source 下拉框 → 选 "GitHub Actions"   ← 关键！
④ 下面的 Custom domain → 留空！什么都别填
⑤ Enforce HTTPS → 默认勾上，不用改
⑥ 点 Save
```

> ⚠️ Custom domain 框**不要填**！那是给"我买了域名想绑上去"用的。留空就行。

### 6.4 工作原理

```
┌─ ui-test job ─────────────────────────────────────────┐
│  1. 装 Java（temurin 17）                              │
│  2. 装 allure-commandline（npm 全局装）                │
│  3. 跑 pytest → 生成 allure-results/（原始数据）        │
│  4. allure generate → 生成 allure-report/（静态 HTML）  │
│  5. upload-pages-artifact → 上传 allure-report 给 Pages│
│  6. deploy-pages → 部署到 evanjiang-jpg.github.io/...  │
│  7. upload-artifact → 把 allure-results 和 allure-report 存 30 天 │
└────────────────────────┬───────────────────────────────┘
                         │ needs: ui-test
                         ▼
┌─ notify job ──────────────────────────────────────────┐
│  8. download-artifact → 取回 allure-results            │
│  9. 发通知（此时 Pages 已经部署好了）                    │
│     → report_url = https://evanjiang-jpg.github.io/... │
│     → 通知里的 "📊 查看完整 Allure 报告" 按钮可直接点击 │
└────────────────────────────────────────────────────────┘
```

### 6.5 为什么拆成两个 job？

通知**必须在 Pages 部署完成之后**发送。如果在同一个 job 里先 `run.py --notify` 再 deploy-pages，用户点按钮时 Pages 还没上线 → 404。

拆 job + `needs: ui-test` 保证时序：

```
ui-test job 完了 → Pages 部署上线 → notify job 才开始 → 发通知 → 用户点按钮 → Pages 已上线 ✅
```

### 6.6 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 点 Allure 按钮报 404 | 没开 Pages | Settings → Pages → Source 选 GitHub Actions |
| 点 Allure 按钮跳流水线 | 旧版本 workflow 的 fallback bug | 已修复，push 最新 workflow 即可 |
| Pages 首次部署慢 | GitHub Pages 首次部署需要几分钟 | 等一次，后面就快了 |
| deploy-pages step 失败 | 没有 pages: write 权限 | workflow job 级别加 `permissions: { pages: write, id-token: write }` |

---

## 七、CI 内置变量（不需要手动配置）

workflow 文件 `.github/workflows/ui-test.yml` 里有一些变量**GitHub 自动注入**，你不用管：

| 变量 | workflow 里的写法 | 说明 |
|------|------------------|------|
| `CI_PIPELINE_ID` | `${{ github.run_id }}` | 流水线运行 ID |
| `CI_COMMIT_AUTHOR` | `${{ github.actor }}` | 触发者的 GitHub 用户名 |
| `CI_COMMIT_MSG` | `${{ github.event.head_commit.message }}` | 本次 commit 的 message |
| `CI_BUILD_URL` | `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` | 流水线运行结果页面链接 |
| `ALLURE_REPORT_URL` | `https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/` | 自动拼接的 GitHub Pages Allure 报告地址 |

通知模板里会用到这些，让接收通知的人能点进流水线页面或 Allure 报告看详情。

---

## 八、完整配置检查清单

配完 Secrets 后确认列表：

- [ ] 钉钉：`DINGTALK_WEBHOOK`（可选）
- [ ] 钉钉机器人关键词已配置 "自动化测试"
- [ ] 飞书：`FEISHU_WEBHOOK`（可选）
- [ ] 飞书机器人关键词已配置 "自动化测试"
- [ ] 邮件：`EMAIL_*` 全套（可选，默认关）
- [ ] GitHub Pages 已开启：Settings → Pages → Source = GitHub Actions

> 💡 **最简配置**：只配飞书（或钉钉）的 webhook 一个值，其他代码自动推断。

---

## 九、本地 .env 快速配置（开发调试用）

CI 上的配置是 GitHub Secrets，本地跑测试用 `config/.env`：

```powershell
# 1. 从模板复制
Copy-Item config\.env.example config\.env

# 2. 打开 config\.env 填上敏感值
```

`.env` 文件内容示例：

```
# ---------- 钉钉 ----------
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=你的token
DINGTALK_SECRET=

# ---------- 飞书 ----------
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/你的token
FEISHU_SECRET=
FEISHU_AT_EMAILS=
FEISHU_AT_ALL=

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
ALLURE_REPORT_URL=
```

> ⚠️ `.env` 文件在 `.gitignore` 里，**不会被提交到 Git**，放心填真实值。

---

## 十、触发 CI 并验证

### 方式 A：手动触发（推荐，不用改代码）

```
仓库页面 → Actions → 左栏 "UI 自动化测试" → 右栏 "Run workflow" 下拉按钮
→ 输入执行范围（默认 p0 or p1）→ 点绿色 "Run workflow"
→ 等跑完（测试用无头浏览器，大概 2-3 分钟，含 Pages 部署）
→ 通知里的 "📊 查看完整 Allure 报告" 按钮点击可访问
```

### 方式 B：push 触发

```powershell
git commit --allow-empty -m "触发 CI 测试"
git push
```

空 commit 也能触发 push 事件的 workflow。

---

## 十一、通知没收到？排查清单

### 11.1 CI 有没有跑？

打开 Actions 页面看最新记录：
👉 https://github.com/evanjiang-jpg/ui_auto_framework/actions

**没记录** → push 的分支不是 main/master，或者 workflow 没生效。

**有记录但红色失败** → 点开看日志，先解决测试本身的问题。

### 11.2 通知走的是 notify job

现在通知拆到了独立的 `notify` job 里，**不要在 ui-test job 里找通知日志**。正确位置：

```
Actions 页面 → 点最新运行 → 左边红/绿的 notify job → 右边展开看日志
```

| 看到 | 含义 |
|------|------|
| `未启用任何通知通道，跳过通知` | webhook Secret 没配或配错 |
| `飞书通知发送成功` | ✅ 发成功了，查飞书群 |
| `飞书通知发送失败: {...}` | webhook 格式错或关键词没配对 |

### 11.3 关键词没配

通知里第一行一定包含 **"自动化测试"**：
- 钉钉机器人关键词要配 **"自动化测试"**
- 飞书机器人关键词要配 **"自动化测试"**

没配关键词 → webhook 发出去平台**静默拒绝** → 收不到消息。

### 11.4 Secret 值有没有空格？

复制粘贴 webhook 地址时容易带上前后空格。确保 Secret 的值**前后没有多余空格和换行**。

### 11.5 三个通道独立开启

有 webhook 就自动开，三个通道互不干扰：

| 配置了 | 效果 |
|--------|------|
| `DINGTALK_WEBHOOK` | 钉钉自动开 |
| `FEISHU_WEBHOOK` | 飞书自动开 |
| `EMAIL_PASSWORD` | 邮件自动开 |
| 多个都配了 | 每个通道各发一条 |

### 11.6 飞书 webhook 要不要加签？

飞书机器人安全设置**三选一**：

| 方式 | 是否要配 FEISHU_SECRET |
|------|----------------------|
| 自定义关键词 | ❌ 不用配 |
| 加签 | ✅ 必须配 |
| IP 白名单 | ❌ 不用配（但不推荐） |

代码里如果 `FEISHU_SECRET` 为空就走无签发送，有值就自动走加签算法。

---

## 十二、常见问题 FAQ

### Q: 修改 Secrets 后需要重新 push 吗？

**不需要**。每次 workflow 运行时 GitHub 都会读取最新的 Secrets。改完直接点 Run workflow 就行。

### Q: 为什么我的 Secret 在 workflow 日志里看不到？

GitHub 会自动把 Secrets 打码（显示为 `***`），这是正常的，防止泄露。

### Q: 想加新的 Secrets，需要改代码吗？

**不需要**。只要 Secret 名和 `config/.env.example` / `notifier.py` 里的 `os.getenv()` 一致，代码自动能读到。

### Q: 多个仓库都想用同一套通知 Secrets？

用 **Organization Secrets**：组织级别配置一次，所有仓库共享。Settings → Secrets and variables → Actions → Organization secrets。

### Q: 本地跑用 `python run.py --notify` 也能发通知吗？

**能**。只要 `config/.env` 里配了对应的值，本地一样会走通知流程。开发调试时可以用自己的测试机器人验证。

### Q: CI 上 Java 和 allure 安装慢？

第一次跑会下载 temurin 17 + npm 包，之后 GitHub Actions 有缓存（setup-python 配了 cache: pip），会快很多。Java 和 npm allure 目前没缓存，每次跑都得装，这是 GitHub Actions 的 tradeoff。

### Q: 通知里的 Allure 报告按钮跳 404？

99% 是 GitHub Pages 没开：Settings → Pages → Source 选 GitHub Actions → Save。等一次 CI 跑完部署成功后再点。