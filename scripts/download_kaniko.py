import urllib.request, os, sys, base64, json

EXECUTOR_PATH = "/kaniko/executor"
KANIKO_VERSION = "v1.24.0"

DOWNLOAD_URLS = [
    f"https://mirror.ghproxy.com/https://github.com/GoogleContainerTools/kaniko/releases/download/{KANIKO_VERSION}/kaniko-executor-1.24.0-linux-amd64",
    f"https://gh-proxy.com/https://github.com/GoogleContainerTools/kaniko/releases/download/{KANIKO_VERSION}/kaniko-executor-1.24.0-linux-amd64",
    f"https://ghproxy.net/https://github.com/GoogleContainerTools/kaniko/releases/download/{KANIKO_VERSION}/kaniko-executor-1.24.0-linux-amd64",
    f"https://github.com/GoogleContainerTools/kaniko/releases/download/{KANIKO_VERSION}/kaniko-executor-1.24.0-linux-amd64",
]

def download_kaniko():
    os.makedirs("/kaniko", exist_ok=True)
    for url in DOWNLOAD_URLS:
        try:
            short = url[:65] + "..." if len(url) > 65 else url
            print(f"尝试下载: {short}")
            urllib.request.urlretrieve(url, EXECUTOR_PATH)
            size = os.path.getsize(EXECUTOR_PATH)
            print(f"  文件大小: {size} bytes")
            if size > 10_000_000:
                break
            print("  文件太小，重试下一个源...")
            os.remove(EXECUTOR_PATH)
        except Exception as e:
            print(f"  失败: {type(e).__name__}: {e}")
            if os.path.exists(EXECUTOR_PATH):
                os.remove(EXECUTOR_PATH)
    else:
        print("ERROR: 所有下载源都失败了!")
        sys.exit(1)
    os.chmod(EXECUTOR_PATH, 0o755)
    print(f"kaniko executor 就绪: {EXECUTOR_PATH} ({os.path.getsize(EXECUTOR_PATH)} bytes)")

def gen_registry_auth():
    os.makedirs("/kaniko/.docker", exist_ok=True)
    reg = os.environ.get("CI_REGISTRY", "")
    user = os.environ.get("CI_REGISTRY_USER", "")
    pwd = os.environ.get("CI_REGISTRY_PASSWORD", "")
    if not reg or not user or not pwd:
        print("WARNING: 缺少 CI_REGISTRY / CI_REGISTRY_USER / CI_REGISTRY_PASSWORD")
        return
    auth = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    config = {"auths": {reg: {"auth": auth}}}
    with open("/kaniko/.docker/config.json", "w") as f:
        json.dump(config, f)
    print(f"Registry 认证写入: {reg}")

if __name__ == "__main__":
    download_kaniko()
    gen_registry_auth()
    print("kaniko 准备完成!")