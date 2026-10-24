# Docker 与 CI/CD

## 一、Docker 一键运行

### 为什么用容器

UI 自动化最典型的坑是「**本地能跑、流水线跑不通**」，根源是浏览器版本、驱动版本、
系统字体、依赖版本不一致。用容器把运行环境固化下来，本地、测试机、CI 三处完全一致。

镜像内已预装：Python 3.10、Chromium + ChromeDriver、Allure 命令行、Java、中文字体、xvfb。

### 构建与运行

```bash
# 方式1：compose（推荐，自动挂载产物目录）
docker compose up --build

# 方式2：原生 docker
docker build -t ui-auto-framework .
docker run --rm --shm-size=2g ui-auto-framework
```

### 常用参数

```bash
# 指定环境
ENV=dev docker compose up --build

# 只跑冒烟，4 进程并行
EXTRA_ARGS="-m smoke -n 4" docker compose up

# 跑完发通知
EXTRA_ARGS="-m smoke --notify" docker compose up --build
```

产物会挂载到宿主机：

```
docker_output/
├── allure-results/     # 原始结果
├── allure-report/      # HTML 报告
├── logs/               # 运行日志
└── screenshots/        # 失败截图
```

### 关键配置说明

| 配置 | 作用 |
|---|---|
| `shm_size: 2gb` | **必须**。Chrome 在容器内默认共享内存只有 64MB，会导致标签页崩溃 |
| `xvfb-run -a` | 提供虚拟显示，无头环境下也能正常跑 UI |
| `--no-sandbox` | 已在 `browser_factory.py` 内置，容器内以 root 运行必需 |
| `fonts-noto-cjk` | 中文字体，缺失会导致页面中文渲染成方框、截图不可读 |

### 常见问题

**1. 构建时下载慢**

Dockerfile 里已注释好国内源替换方式，取消注释即可使用阿里云 apt/pip 源。

**2. 容器内 Chrome 启动崩溃**

检查 `shm_size` 是否已配置为 2GB 以上；仍异常时可加 `--disable-dev-shm-usage`（已内置）。

**3. 需要真实 Chrome 而不是桩驱动**

把 `config/environments.yaml` 里的 `use_stub_browser` 改为 `false`。

---

## 二、CI/CD 集成

三套配置开箱即用，**触发规则与执行范围保持一致**：

| 触发场景 | 执行范围 | 目的 |
|---|---|---|
| MR / PR / 合入主干 | `smoke` | 快速卡点，必须全过才能合并 |
| 打 tag / 手动触发 | `p0` | 高优用例回归 |
| 夜间定时 / 手动全量 | `p0 or p1` | 完整回归 |

统一带 `--reruns 2`（抗偶发抖动）、统一 `--notify`（结果推送）、
统一保留 `logs/`、`screenshots/`、`allure-results/` 作为产物。

### GitLab CI

配置文件：`cicd/.gitlab-ci.yml`（复制到项目根目录改名 `.gitlab-ci.yml`）

三阶段：`prepare → smoke → regression`，pip 依赖按分支缓存。
Allure 结果作为 artifact 保留 30 天。

需要在 **Settings > CI/CD > Variables** 配置钉钉/邮箱相关变量（勾选 Protected/Masked）。

### Jenkins

配置文件：`cicd/Jenkinsfile`

- 声明式流水线，支持参数化构建（环境、范围、并行数、是否通知）
- 依赖 Allure Jenkins Plugin 展示报告
- 凭据通过 `credentials()` 读取，不落明文
- `post.always` 归档日志与截图

需在 **Manage Jenkins > Credentials** 中创建：
`ui-test-dingtalk-webhook`、`ui-test-dingtalk-secret`、`ui-test-email-password`。

### GitHub Actions

配置文件：`.github/workflows/ui-test.yml`

- 五类触发：push、pull_request、schedule、workflow_dispatch、tag
- 使用 `actions/setup-python` 的 pip 缓存
- 测试结果通过 `continue-on-error` + 汇总步骤判定，保证失败时仍能上传产物
- Secrets 未配置时自动不启用对应通知通道

需在 **Settings > Secrets and variables > Actions** 配置钉钉/邮箱变量。

---

## 三、CI 环境变量约定

框架会自动读取以下变量填充通知内容（各平台变量名可能不同，按上表映射即可）：

| 变量 | 含义 |
|---|---|
| `ENV` | 执行环境 |
| `CI_PIPELINE_ID` | 流水线编号 |
| `CI_COMMIT_AUTHOR` | 提交人 |
| `CI_COMMIT_MSG` | 提交信息 |
| `CI_BUILD_URL` | 构建页地址（通知里点击直达） |

---

## 四、失败时怎么排查

1. 看 **Allure 报告**：失败用例自动附带截图、页面源码、异常堆栈
2. 看 **logs/**：完整 DEBUG 日志，含接口请求响应与元素操作记录
3. 看 **screenshots/**：本地 PNG，便于直接下载查看
4. 看通知里的**失败用例清单**：定位是哪一个模块、哪一条用例

---

## 五、退出码约定

`run.py` 会把 pytest 退出码原样透传：

- `0`：全部通过（流水线绿）
- 非 `0`：存在失败用例（流水线红）

流水线无需额外解析报告即可判定成功失败。
