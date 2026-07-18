# USB 反向代理隧道——手机通过电脑免费上网

## 用途
让手机通过 USB 线连接到电脑后，使用电脑的局域网免费上网，而不是消耗手机 SIM 流量。

## 原理
电脑上的 v2rayN 代理（SOCKS5 端口 10808）通过 ADB Reverse 转发到手机上。
手机将其系统代理设为 127.0.0.1:10808，所有网络通讯走 USB 线到电脑，再由电脑访问互联网。

## 启用
```bash
# 一条命令开启
adb -s <设备> reverse tcp:10808 tcp:10808
adb -s <设备> shell "settings put global http_proxy 127.0.0.1:10808"
```

或使用统一脚本：
```bash
~/.hermes/scripts/adb-connect.sh proxy   # 开启
~/.hermes/scripts/adb-connect.sh noproxy # 关闭，用手机自身网络
```

## 验证
```bash
adb shell curl -x socks5://127.0.0.1:10808 https://www.google.com -o /dev/null -w '%{http_code}'
# 返回 200 即成功
```

## 注意事项
- 隧道在以下情况失效：USB 拔除、ADB 服务重启、手机重启
- 重新连接后需要再次运行开启命令
- 共享的是电脑的网络，电脑连不上的网站手机同样连不上
- 手机通过自身移动网络访问则不受电脑限制
- 此方案零费用，仅需 USB 线连接
- 作为备用方案：当电脑上不了网时，手机自动切回移动数据
