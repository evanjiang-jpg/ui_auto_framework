# ==============================================================
# UI 自动化测试镜像
#
# 构建：docker build -t ui-auto-framework .
# 运行：docker compose up --build
#
# 镜像内已包含 Chrome / ChromeDriver / Allure / Java / 中文字体，
# 保证本地、测试机与 CI 运行环境完全一致。
# ==============================================================
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

# --------------------------------------------------------------
# 1) 基础工具 + Chrome 运行库 + 中文字体 + xvfb 虚拟显示
#    国内构建可先替换 apt 源为阿里云，速度更快：
#    RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
# --------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget curl unzip gnupg ca-certificates \
        xvfb \
        fonts-noto-cjk \
        chromium chromium-driver \
        default-jre-headless \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# --------------------------------------------------------------
# 2) Allure 命令行（生成 HTML 报告需要）
# --------------------------------------------------------------
ARG ALLURE_VERSION=2.24.0
RUN wget -q -O /tmp/allure.tgz \
        "https://github.com/allure-framework/allure2/releases/download/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.tgz" \
    && tar -xzf /tmp/allure.tgz -C /opt \
    && ln -s "/opt/allure-${ALLURE_VERSION}/bin/allure" /usr/bin/allure \
    && rm /tmp/allure.tgz \
    && allure --version

# --------------------------------------------------------------
# 3) Python 依赖（先装依赖，利用镜像层缓存）
#    国内构建可加：-i https://mirrors.aliyun.com/pypi/simple/
# --------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------
# 4) 复制工程
# --------------------------------------------------------------
COPY . .

# --------------------------------------------------------------
# 5) 默认执行：无头模式跑全量，不打开报告（结果挂载到宿主机）
# --------------------------------------------------------------
CMD ["sh", "-c", "xvfb-run -a python run.py --no-report ${EXTRA_ARGS:-}"]
