# Hermes Gateway Telegram SSL 诊断 (Termux)

## 症状

在 Android Termux 上启动 Hermes Gateway，日志显示：

```
WARNING gateway.platforms.telegram: [Telegram] Connect attempt 1/8 failed: 
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: 
unable to get local issuer certificate (_ssl.c:1032)
```

## Termux 特有问题诊断

### 诊断步骤

1. **确认 SSL 证书链是否正常**
   ```bash
   python3 -c "import ssl; ctx=ssl.create_default_context(); print(ctx.cert_store_stats())"
   ```
   Android Termux 默认从系统区域加载 CA 证书。如果 certifi 正确安装，Python 会自动使用 certifi。SSL_CERT_FILE 通常不需要手动设置。

2. **区分证书问题和代理问题**
   SSL 错误不一定真是证书问题。当 HTTP CONNECT 代理通道超时时，httpx 可能将超时报为 SSL 错误。
   ```bash
   timeout 30 python3 -c "
   import httpx, time
   with httpx.Client(
       mounts={'all://': httpx.HTTPTransport(proxy='http://127.0.0.1:1080')},
       verify='/path/to/certifi/cacert.pem',
       timeout=30
   ) as c:
       t0=time.time()
       r=c.get('https://api.telegram.org/bot<TOKEN>/getMe')
       print(f'{time.time()-t0:.1f}s status={r.status_code}')
   "
   ```
   - 10s 超时 + SSL 错误 → 可能是代理通道超时（误报）
   - 30s 超时 + 仍 SSL 错误 → 代理或证书问题
   - ReadTimeout（非 SSL 错误）→ 代理通道已通但响应慢

3. **用 curl 测试同一代理**
   ```bash
   curl -x http://127.0.0.1:1080 -sk --connect-timeout 10 "https://api.telegram.org/bot<TOKEN>/getMe"
   ```

### 根因判断

当满足以下条件时，SSL_CERT_FILE 不是问题：
- ssl.create_default_context() 返回 150+ CA 证书
- certifi.cacert.pem 存在且非空
- Python httpx 直接连 HTTPS 正常（不走代理）

真正的根因是代理层的问题——代理到 Telegram 的网络通道超时或断开，httpcore/httpx 把连接中断误报为 SSL 错误。

## 修复策略

### 1. 代理配置（推荐）

Termux 上 Hermes Gateway Telegram 必须通过代理。在 ~/.hermes/.env 配：
```
TELEGRAM_PROXY=http://127.0.0.1:1080
```

### 2. SSL_CERT_FILE（通常不需要）

理论上可加，但不是根因。不建议花时间调试这个。

### 3. 入口脚本格式

Termux 入口脚本必须：
```bash
#!/data/data/com.termux/files/usr/bin/bash
export HOME=/data/data/com.termux/files/home
export PATH=/data/data/com.termux/files/usr/bin:$PATH
export PYTHONPATH=/data/data/com.termux/files/usr/lib/python3.13/site-packages:$PYTHONPATH
exec /data/data/com.termux/files/usr/bin/python3 -m hermes_cli.main "$@"
```

## 验证 Gateway 连接

```bash
hermes gateway run --verbose 2>&1 | grep -iE "telegram|SSL|proxy|connect|enabled"
```

正常连接日志：`[Telegram] Connected via proxy ...`

## 注意事项

- Termux 上 `hermes gateway start` 不支持（需 systemd），必须用 `hermes gateway run`
- SSL 错误信息具有欺骗性——先检查代理连通性，别折腾证书
- python-telegram-bot 22.x 不依赖 cryptography（有 except ImportError 兜底）