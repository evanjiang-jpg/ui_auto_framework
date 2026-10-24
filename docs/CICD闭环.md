# CI/CD 闭环文档

> 对标京东研发体系，用 GitHub Actions 实现完整的 CI/CD 流水线

---

## 🎯 一、CI 和 CD 到底是什么

### CI（Continuous Integration）持续集成

**开发者频繁把代码合到主分支上，每次合入都自动跑构建+测试，尽早发现问题。**

```
你本地写代码 → git commit → git push(main)
                              ↓
                    ┌── CI 流水线自动触发 ──┐
                    │ ① 拉代码               │
                    │ ② 装依赖               │
                    │ ③ 跑 lint / 单测 / 集成测试 │
                    │ ④ 生成报告             │
                    │ ⑤ 失败 → 通知你改       │
                    │ ⑥ 成功 → 交给 CD        │
                    └────────────────────────┘
```

**核心价值：** 把"提交后手工执行的测试验证"变成"自动执行"，**提交代码 → 知道结果** 不超过 10 分钟。

---

### CD（两个含义，行业通用定义）

#### ① 持续交付（Continuous Delivery）—— 京东绝大多数业务线默认

CI 跑通后，代码**自动进入"随时可上线"的就绪状态**，但**最终点"部署到生产"的按钮要人工按**。

```
CI 通过 ✅ → 构建制品 → 部署到 BOE/PPE → 人工审批 → 上线生产
                                    ↑
                            测试同学 / 研发 Review 点通过
```

#### ② 持续部署（Continuous Deployment）—— 京东内部工具 / 低风险场景

CI 跑通后，**全自动一路推到生产环境**，不需要任何人审批。

```
CI 通过 ✅ → 构建制品 → BOE/PPE 自动验证 → 预发 → 灰度 1% → 全量生产
                                                    ↑
                                            全自动化，零人工干预
```

---

## 🏗️ 二、你的项目完整 CI/CD 闭环

```
git push(main/master)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ ① CI 阶段（ui-test job）                                │
│                                                         │
│  ① Checkout 拉代码                                      │
│  ② 装 Python 3.10 + Java 17 + Allure CLI               │
│  ③ pip install 装依赖                                   │
│  ④ pytest 跑用例（4 进程并行 + 失败重跑）               │
│  ⑤ Allure generate → 静态 HTML 报告                     │
│  ⑥ upload-pages-artifact → 上传报告                     │
│  ⑦ deploy-pages → 部署到 GitHub Pages                   │
│  ⑧ upload-artifact → 保存 logs/screenshots/results      │
│                                                         │
│  质量门禁：用例全过才能往下走                             │
└─────────────────────┬───────────────────────────────────┘
                      │ needs: ui-test
                      ▼
┌─────────────────────────────────────────────────────────┐
│ ② CD-镜像 阶段（image job）—— 对标京东 JDOS 制品库      │
│                                                         │
│  ① docker/login-action → 登录 GHCR                     │
│  ② docker/metadata-action → 自动打 tag                 │
│     （latest / main-{sha} / v1.0.0...）                 │
│  ③ docker/build-push-action → 构建镜像 → 推 GHCR        │
│                                                         │
│  产物可复用：docker pull ghcr.io/evanjiang-jpg/ui_auto_framework
└─────────────────────┬───────────────────────────────────┘
                      │ needs: image
                      ▼
┌─────────────────────────────────────────────────────────┐
│ ③ CD-部署 阶段（deploy-test job）—— 对标京东 BOE        │
│                                                         │
│  ① 环境审批：GitHub Environments 配置 test 环境         │
│     → Required reviewers: 勾选你自己                   │
│     → CD 走到这会暂停，等你点 ✅ 批准                   │
│                                                         │
│  ② SSH 到测试服务器（appleboy/ssh-action）              │
│     git pull --ff-only main                             │
│     docker pull ghcr.io/.../ui_auto_framework:latest    │
│     docker compose up -d --remove-orphans               │
│     docker image prune -f                               │
│                                                         │
│  ③ 线上冒烟：docker compose ps 验证容器启动              │
│                                                         │
│  注意：这步需要配 DEPLOY_HOST / DEPLOY_USER /           │
│  DEPLOY_SSH_KEY / DEPLOY_PATH 四个 Secret              │
│  如果没配这些，这步自动跳过，不影响 CI 和 镜像构建      │
└─────────────────────┬───────────────────────────────────┘
                      │ needs: [ui-test, image, deploy-test]
                      │ if: always() ← 不管哪步失败都发通知
                      ▼
┌─────────────────────────────────────────────────────────┐
│ ④ 通知阶段（notify job）                                │
│                                                         │
│  下载 artifact → 跑 run.py --notify-only               │
│  → 飞书卡片（✅ 17 通过 0 失败 + Allure 链接）          │
│  → 钉钉 Markdown                                        │
│  → QQ 邮件                                              │
│                                                         │
│  三通道独立，互不影响                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 🔑 三、CD 关键概念

### 3.1 制品库（Artifact Registry）—— 对标京东 JDOS

| 概念 | 京东内部 | GitHub Actions 对应 |
|------|---------|-------------------|
| 制品存储 | JDOS / JRPM | GitHub Container Registry (GHCR) |
| 镜像命名 | jdos.jd.com/... | ghcr.io/evanjiang-jpg/ui_auto_framework |
| 认证方式 | 内网 token | GITHUB_TOKEN（自动） |
| 复用方式 | `docker pull jdos.jd.com/xxx` | `docker pull ghcr.io/evanjiang-jpg/ui_auto_framework` |

**你的 Dockerfile 已经就位**（含 Chrome/Allure/Java 全套运行时），CI 跑过就能构建可用镜像。

### 3.2 环境审批（Environment Approval）—— 对标京东上线审批

```yaml
# workflow 里写：
deploy-test:
  runs-on: ubuntu-latest
  environment:
    name: test                    # ← 对应 GitHub Environments 里的名字
    url: ${{ secrets.DEPLOY_URL }}
```

然后去 **仓库 Settings → Environments → New environment**：

```
Name: test
Required reviewers: ☑ evanjiang-jpg   ← 勾上自己，审批会暂停等你点
Deployment branches: Selected branches → main, master
Wait timer: 0 (不需要等)
```

**效果：** CD 流水线跑到 deploy-test 时，会在 GitHub 上显示 "Waiting for approval"，你点 **Review deployments → Approve** 才继续往下走。这就是"持续交付"模式。

### 3.3 持续交付 vs 持续部署 — 你的项目可以同时支持

| 模式 | 怎么触发 | 场景 |
|------|---------|------|
| **持续交付（有审批）** | 正常 push main | 日常开发，测试确认后再部署 |
| **持续部署（全自动）** | 手动 workflow_dispatch + deploy_enabled=false 跳过审批检查 | 内部工具、紧急 Bug 修复 |
| **只构建镜像不部署** | PR 分支触发 | 开发中验证代码没问题，但不影响线上 |

---

## 📦 四、你的项目现在能产出什么

| 产物 | 存储位置 | 谁能访问 | 对应京东概念 |
|------|---------|---------|-------------|
| Allure HTML 报告 | GitHub Pages | 公开仓库：所有人可见 | 测试报告归档平台 |
| Docker 镜像 | ghcr.io | 公开仓库：所有人可 pull | JDOS 制品库 |
| 测试日志 | GitHub Actions Artifacts | 仓库成员 | 工单追溯附件 |
| 失败截图 | GitHub Actions Artifacts | 仓库成员 | 故障现场快照 |
| 飞书卡片通知 | 飞书群 | 群组内 | 上线通知 |

---

## 🧭 五、触发规则一览

| 触发方式 | CI (ui-test) | 镜像 (image) | 部署 (deploy-test) | 通知 (notify) |
|---------|:---:|:---:|:---:|:---:|
| push main/master | ✅ | ✅ | ✅ (需配 DEPLOY_HOST) | ✅ |
| PR → main/master | ✅ | ❌ | ❌ | ✅ |
| 每日定时 cron | ✅ | ✅ | ✅ (需配 DEPLOY_HOST) | ✅ |
| 手动 Run workflow | ✅ | ✅ | ✅ (deploy_enabled=true 时) | ✅ |
| 改 docs/*.md | ❌ 跳过 | ❌ | ❌ | ❌ |

---

## 🛠️ 六、配 CD 部署的完整步骤

### 6.1 准备一台测试服务器

```bash
# 生成 SSH key（本地 Windows PowerShell）
ssh-keygen -t ed25519 -C "github-actions"
# 会生成：
#   ~/.ssh/id_ed25519       ← 私钥（发给 GitHub Secrets）
#   ~/.ssh/id_ed25519.pub   ← 公钥（加到测试服务器 ~/.ssh/authorized_keys）
```

### 6.2 测试服务器上

```bash
# 装 Docker + Docker Compose（略）
# 加公钥
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your-server-ip

# clone 你的仓库
git clone git@github.com:evanjiang-jpg/ui_auto_framework.git /opt/ui_auto_framework
```

### 6.3 GitHub Secrets（Settings → Secrets and variables → Actions）

| Secret 名 | 值 | 示例 |
|-----------|---|------|
| `DEPLOY_HOST` | 服务器 IP | `192.168.1.100` |
| `DEPLOY_USER` | SSH 用户名 | `root` |
| `DEPLOY_SSH_KEY` | 私钥内容（整段粘贴） | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |
| `DEPLOY_PATH` | 服务器上的仓库路径 | `/opt/ui_auto_framework` |
| `DEPLOY_PORT` | SSH 端口（可默认 22） | `22` |
| `DEPLOY_URL` | 服务器访问地址（可选，纯展示用） | `http://192.168.1.100` |

### 6.4 开 GitHub Environments 审批（可选但推荐）

```
仓库 Settings → Environments → New environment
Name: test
Required reviewers: ☑ 你的 GitHub 用户名
保存
```

### 6.5 Push 触发，看效果

```bash
git add .
git commit -m "feat: 加 CI/CD 完整流水线"
git push
```

流水线会在 deploy-test 那步暂停等你审批。

---

## ❓ 七、为什么 deploy-test 有这层 if 判断

```yaml
deploy-test:
  if: |
    github.event_name != 'pull_request' &&
    secrets.DEPLOY_HOST != ''
```

| 场景 | 结果 |
|------|------|
| 本地开发机 push | ✅ 跑（如果配了 DEPLOY_HOST） |
| PR 分支（开发中） | ❌ 跳过（避免部署半成品） |
| 没配 DEPLOY_HOST | ❌ 自动跳过（不想配服务器也不影响 CI） |
| 手动触发 deploy_enabled=false | ❌ 跳过（临时跳过部署） |

**设计原则：** 没配 CD 不影响 CI，PR 永远不触发生产动作。

---

## 🔄 八、进阶玩法（对标京东灰度发布）

### 8.1 预发 → 生产双环境

```yaml
deploy-pre:
  environment:
    name: pre              # Settings → Environments → pre
  steps:
    - run: docker compose up -d    # 部署预发

deploy-prod:
  needs: deploy-pre
  environment:
    name: prod             # 单独的审批人！
  steps:
    - run: docker compose up -d    # 部署生产
    - run: |                  # 冒烟验证
        curl -fsS http://.../health
```

### 8.2 灰度发布（手动分批）

```yaml
deploy-canary:
  environment:
    name: canary
  steps:
    - run: docker compose up -d --scale app=1    # 1 台

deploy-full:
  needs: deploy-canary
  environment:
    name: prod
  steps:
    - run: docker compose up -d --scale app=10   # 全量
```

### 8.3 制品签名（对标京东 DevSecOps）

```yaml
sign-artifact:
  steps:
    - run: cosign sign ghcr.io/evanjiang-jpg/ui_auto_framework:${{ github.sha }}
    - run: cosign verify ghcr.io/evanjiang-jpg/ui_auto_framework:${{ github.sha }}
```

---

## 📊 九、完整 CI/CD 全景图（你的项目 vs 京东内部）

| 阶段 | 京东内部 | 你的 GitHub Actions |
|------|---------|-------------------|
| 代码托管 | 京东 GitLab | GitHub |
| CI 触发 | webhook 自动 | push/PR/schedule |
| 测试执行 | Jenkins Runner / 京东 TestOps | ubuntu-latest Runner |
| 报告生成 | Allure Server | GitHub Pages + Allure HTML |
| 制品库 | JDOS | GHCR |
| 部署审批 | Flow / 京东发布平台 | GitHub Environments |
| 测试环境 | BOE | 自建服务器（SSH） |
| 预发/灰度 | PPE / 发布系统 | 可加 deploy-pre / deploy-canary |
| 通知通道 | 京东 IM / 邮件 | 飞书 / 钉钉 / 邮件 |
| 安全扫描 | DevSecOps 自动扫 | 可加 Trivy / Snyk |
| 日志归档 | ELK / 京东日志平台 | GitHub Artifacts + Pages |