# UI 自动化测试框架

基于 **pytest + Selenium + Allure + PO 模式** 的企业级 UI 自动化测试骨架，内置参数分层管理、多环境配置、接口前置、数据库断言、稳定性治理、失败现场捕获、通知与 CI/CD 集成。

所有模块按「单一职责」拆分，`conftest.py` 只做装配，业务能力各自独立成模块，避免越加越乱。

---

## 一、特性一览

| 能力 | 说明 | 位置 |
|---|---|---|
| 参数分层管理 | 环境层 / 会话层 / 用例层 / 动态层四级隔离 | `config/`、`common/global_context.py` |
| 多环境配置 | default + 环境层 + 本地覆盖三层合并，切换环境不改代码 | `common/env_manager.py` |
| 数据驱动 | yaml/json 自动识别，支持占位符、笛卡尔积、公共参数 | `common/data_reader.py` |
| PO 模式 | 元素定位与业务动作分离，登录态失效自动重登重试 | `pages/` |
| 依赖注入 | 会话级登录态一次登录全程复用 | `plugin/fixtures.py` |
| 接口前置 | 接口造数/接口登录，速度提升 3-10 倍，结束自动清理 | `common/api_client.py` |
| 数据库断言 | 支持 sqlite/mysql/pg，含异步最终一致性的轮询等待 | `common/db/` |
| 稳定性治理 | 条件等待、指数退避重试、用例级 flaky 重跑 | `common/retry.py` |
| 失败现场捕获 | 自动截图 + 页面源码 + 堆栈，重试时不重复截图 | `plugin/hooks_screenshot.py` |
| Allure 标签自动化 | 标签写在数据文件里，钩子自动注入 | `plugin/hooks_tags.py` |
| 通知 | 钉钉（加签/@人）+ 邮件（HTML+附件），模板可自定义 | `common/notifier/` |
| 统一入口 | 一个命令覆盖本地与 CI | `run.py` |
| CI/CD | GitLab / Jenkins / GitHub Actions 三套配置 | `cicd/`、`.github/` |
| 容器化 | 一键构建含 Chrome 的镜像，环境完全一致 | `Dockerfile` |

---

## 二、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. （可选）配置敏感信息与通知
cp config/.env.example config/.env
#   编辑 config/.env，填钉钉 webhook / 邮箱 SMTP；不启用通知可跳过

# 3. 一键执行
python run.py
```

> 默认 `test` 环境、`use_stub_browser: true`（内置桩驱动），无需安装浏览器即可跑通全部用例。

常用命令：

```bash
python run.py --list-envs                      # 查看可用环境
python run.py --list-markers                   # 查看全部标签
python run.py -e dev -m smoke -n 4             # dev 环境冒烟，4 进程并行
python run.py -k order -x                      # 只跑订单相关用例，失败即停
python run.py -m "p0 and not slow" --reruns 2  # 高优用例，失败重跑 2 次
python run.py --api-login -m smoke             # 接口登录替代 UI 登录
python run.py --no-report --notify             # CI：不出报告 + 发通知
```

---

## 三、目录结构

```
ui_auto_framework/
├── conftest.py              # 仅做装配：声明加载哪些 pytest 插件
├── pytest.ini               # 运行配置 + 标签注册
├── run.py                   # 统一执行入口
├── requirements.txt
│
├── config/                  # 配置（唯一配置源）
│   ├── environments.yaml    #   多环境配置
│   ├── database.yaml        #   数据库连接（按环境）
│   ├── local.yaml.example   #   本地个人覆盖层示例（不入库）
│   └── .env.example         #   敏感信息与通知配置示例
│
├── common/                  # 公共能力（一个文件一个职责）
│   ├── env_manager.py       #   多环境配置管理
│   ├── logger.py            #   日志（控制台 + 文件）
│   ├── global_context.py    #   全局/线程隔离上下文
│   ├── data_reader.py       #   测试数据加载
│   ├── api_client.py        #   接口客户端（前置造数/接口登录）
│   ├── mock_api.py          #   接口桩后端（无后端时演示用）
│   ├── auth_manager.py      #   登录态缓存与自动重登
│   ├── retry.py             #   等待与重试工具
│   ├── screenshot.py        #   失败现场捕获
│   ├── browser_factory.py   #   浏览器工厂
│   ├── stub_driver.py       #   演示用桩驱动
│   ├── db/                  #   数据库访问 + 断言
│   └── notifier/            #   通知（模型/模板/通道/门面）
│
├── plugin/                  # pytest 插件（各钩子点独立成文件）
│   ├── options.py           #   命令行参数、环境切换
│   ├── fixtures.py          #   全部 fixture
│   ├── hooks_tags.py        #   数据驱动自动打标签
│   └── hooks_screenshot.py  #   失败自动截图
│
├── pages/                   # 页面对象（PO 模式）
├── testcases/               # 测试用例
├── data/                    # 测试数据 + schema.sql
├── templates/notify/        # 自定义通知模板（可选）
├── docs/                    # 使用文档
├── cicd/                    # GitLab / Jenkins 流水线配置
└── .github/workflows/       # GitHub Actions 配置
```

**分层原则**：`config → common → pages → testcases`，依赖单向向下；`plugin` 只依赖 `common` 与 `pages`，用例不反向依赖框架内部。

---

## 四、文档索引

| 文档 | 内容 |
|---|---|
| `docs/架构说明.md` | 分层设计、钩子点说明、如何扩展新能力 |
| `docs/多环境配置.md` | 三级合并规则、环境切换、密钥注入 |
| `docs/数据库断言.md` | 连接配置、断言 API、异步最终一致性 |
| `docs/重试与稳定性.md` | 三层稳定性治理 + 标签规范 |
| `docs/通知与模板.md` | 钉钉/邮件配置与模板自定义 |
| `docs/Docker与CI.md` | 容器化运行与三套流水线接入 |

---

## 五、接入真实项目要改什么

框架与业务解耦，接入时只需要改这几处，其余代码不动：

1. **配置**：`config/environments.yaml` 填真实域名；`config/database.yaml` 填真实库
2. **关掉演示开关**：`use_stub_browser: false`（用真实 Chrome）、`api_mock: false`（走真实接口）
3. **页面对象**：`pages/` 下按真实页面补元素定位与业务动作
4. **测试数据**：`data/` 下换成自己的数据文件
5. **用例**：`testcases/` 下换成自己的业务用例
6. **敏感信息**：`config/.env` 或 CI 平台加密变量注入

---

## 六、常见报错排查

**1. `ModuleNotFoundError: No module named 'common'`**

项目根目录**不能**放 `__init__.py`。pytest 以「向上找第一个不含 `__init__.py` 的目录」判定项目根，
根目录放了 `__init__.py` 会把项目根推到上一级，导致包找不到。
本框架已在 `pytest.ini` 配置 `pythonpath = .` 作为双保险。

**2. `fixture 'xxx' not found`**

检查参数名与 `plugin/fixtures.py` 里的 fixture 名是否**完全一致**；fixture 靠名字匹配注入，不需要 import。
本框架的 conftest 通过 `pytest_plugins` 加载插件，若插件模块名写错，所有 fixture 都会失效。

**3. 收集到 0 个用例**

检查文件名 `test_*.py`、类名 `Test*`（且无 `__init__`）、函数名 `test_*`；
用 `python -m pytest --collect-only -q` 定位。

**4. 报 `unknown hook` 或插件冲突**

`pytest_configure` 等钩子的**参数名必须与 hookspec 一致**（如固定为 `config`），
不能为了避让同名变量而改名，否则 pluggy 会直接拒绝注册。

**5. allure 报告没生成**

`allure-pytest` 只产出原始结果，生成 HTML 还需安装 allure 命令行（需 Java）：
`npm i -g allure-commandline`。未安装时框架会跳过并在控制台提示，不影响用例执行。
