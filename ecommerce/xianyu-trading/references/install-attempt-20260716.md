# Xianyu 工具试用记录 2026-07-16

## 测试环境
- macOS 15.7, Intel Mac
- Docker Desktop v28.1.1
- Python 3.11/3.13/3.14（无 3.12）
- Proxy: 127.0.0.1:10808

## GooFish-AIMonitor 安装结果：失败

### 尝试途径
1. **Docker Compose build** — Docker Hub registry 连不上
   - 错误：`failed to authorize: failed to fetch oauth token` IPv6 重置
   - `docker compose up -d` 失败（缺 data/secret.env）
   - `docker compose pull` 失败（无预构建镜像）
   - `docker build --network=host` 超时 300s
2. **pip install 直接跑** — 项目要求 Python ≥3.12，系统无 3.12
   - uv venv --python 3.11 → 版本不满足
   - uv venv --python 3.13 → uv pip install 卡住（超时 300s）
   - pip3 install 通过代理（127.0.0.1:10808）→ 成功安装 deps
   - patch pyproject.toml `requires-python = ">=3.11"` → 未重新尝试安装
3. **Playwright 直接跑** — 闲鱼反爬拦截
   - headless → 超时（闲鱼检测 headless 浏览器）
   - 非 headless 未尝试（已耗时过久）

### 关键依赖状态
- fastapi/uvicorn/pydantic/httpx → openbb-env 中已有
- sqlalchemy/apscheduler → 通过代理 pip 安装成功
- playwright v1.61.0 → openbb-env 中已有，浏览器已下载（chromium-1228）

## 用户闲鱼链接
- 创想三维 K1：待定？
- Voron Tiny-T：待定？
