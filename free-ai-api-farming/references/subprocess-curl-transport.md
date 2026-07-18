# Subprocess curl transport（curl_cffi 代理不可用时的备用方案）

## 问题

macOS 上常见代理（Google Chrome 服务，端口 10808，支持 HTTP CONNECT + SOCKS5）使用系统 `curl` 时正常，但 `curl_cffi` 的 bundled libcurl 无法通过该代理建立连接。导致 grok-build-auth 的注册阶段永远 curl timeout。

## 原因

`curl_cffi` 在 macOS 上使用自带的 libcurl（非系统 libcurl），其代理/SSL 实现与系统代理存在兼容性问题。`proxies` 字典和 `http_proxy` 环境变量均无效。

## 解法：CurlSubprocessTransport

在 `xconsole_client/curl_subprocess.py` 中实现了一个 switch transport，直接调用系统 `curl` 二进制并通过 `-x` 参数传入代理。

### 强制切换到系统子进程模式（2026-07-16 实测）

`fingerprint.py` 的自动 fallback 逻辑只在 `curl_cffi` 导入失败时触发。如果 `curl_cffi` 已安装但 TLS 不通（如本机 v2rayN 代理情况），**必须显式移除 curl_cffi** 才能触发子进程模式：

```bash
# 移除 curl_cffi 强制走系统 curl 子进程
rm -rf /tmp/grok-build-auth/.venv/lib/python3.11/site-packages/curl_cffi*

# 验证模式切换
cd /tmp/grok-build-auth && source .venv/bin/activate
python3 -c "from xconsole_client.fingerprint import FingerprintTransport; t = FingerprintTransport(proxy='http://127.0.0.1:10808'); print(t._mode)"
# 应输出: subprocess
```

### 加代理环境变量

```bash
HTTPS_PROXY=socks5://127.0.0.1:10808 HTTP_PROXY=socks5://127.0.0.1:10808 \
  YESCAPTCHA_API_KEY=xxx python3 run.py -n 1 -e mailtm --no-oauth
```

### 文件位置

注册机项目目录下的 `xconsole_client/curl_subprocess.py`（独立文件，不依赖 curl_cffi）

### 核心逻辑

```python
class CurlSubprocessTransport:
    def request(self, method, url, *, headers, body=None):
        cmd = ["curl", "-s", "-S", "-i", "--max-time", str(int(timeout))]
        if proxy:
            cmd.extend(["-x", proxy])
        if method == "POST" and body:
            cmd.extend(["-X", "POST", "--data-binary", "@-"])
        # 按优先级顺序加headers
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
        cmd.append(url)
        r = subprocess.run(cmd, input=body, capture_output=True, timeout=...)
        # 解析返回的 HTTP 状态、headers、set-cookie、body
```

### 集成到 fingerprint.py

`FingerprintTransport` 优先尝试 `curl_cffi`，若其代理不通则 fallback 到 `CurlSubprocessTransport`：

```python
class FingerprintTransport:
    def __init__(self, ..., proxy=None):
        if _HAS_CURL_CFFI:
            self._session = cc_requests.Session(...)
            # curl_cffi可能不认proxy，但没关系
        else:
            self._session = CurlSubprocessTransport(...)
        self._mode = "curl_cffi" if _HAS_CURL_CFFI else "subprocess"
```

### 注意

- 子进程方式**没有 TLS 指纹**，可能被 Cloudflare 拦截
- Cookie 管理由 `XConsoleAuthClient` 自己维护，不在传输层做
- 适用于代理兼容性验证和链路调试，生产环境建议用正常 curl_cffi + 兼容代理
