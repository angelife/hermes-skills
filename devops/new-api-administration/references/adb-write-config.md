# 通过 ADB 在 Android 设备上写配置文件

## 问题

`adb shell run-as com.termux sh -c 'echo lines > file'` 会报 Permission denied，因为 `>` 重定向在 run-as 生效前执行。

## 正确方法

### 方法一：cp 从 /sdcard/Download/（推荐，验证可行）

```bash
# 1. 推送到 /sdcard/Download/（Android 共享存储，所有 app 可读写）
adb -s <serial> push modified_config.yaml /sdcard/Download/config_new.yaml

# 2. 用 run-as 复制到目标路径
adb -s <serial> shell "run-as com.termux cp /sdcard/Download/config_new.yaml /data/data/com.termux/files/home/.hermes/config.yaml"

# 3. 验证
adb -s <serial> shell "run-as com.termux head -6 /data/data/com.termux/files/home/.hermes/config.yaml"
```

`/sdcard/Download/` 在 Android 所有版本都存在且权限宽松，是最可靠的中转目录。比 `/data/local/tmp/` 更通用。

### 方法一（旧版）：cp 从 /data/local/tmp/

```bash
# 1. 推送到 /data/local/tmp/
adb push /tmp/source_file /data/local/tmp/source_file

# 2. 用 cp 复制到目标
adb shell "run-as com.termux sh -c 'cp /data/local/tmp/source_file /data/data/com.termux/files/home/.hermes/config.yaml'"
```

/data/local/tmp/ 对所有 shell 用户可读写，不受 run-as 权限限制。

### 方法二：Python 写文件（在设备内）

```bash
adb shell "run-as com.termux sh -c '
PREFIX=/data/data/com.termux/files/usr
PATH=\\$PREFIX/bin:/system/bin
\\$PREFIX/bin/python3.13 -c \"import sys; open(sys.argv[1],\\\"w\\\").write(sys.stdin.read())\" /data/data/com.termux/files/home/.hermes/config.yaml << EOF
content here
EOF
'"
```

注意：Python heredoc 在嵌套 sh -c 中引号处理极为复杂，不推荐。

### 方法三：sed 替换（已存在的文件）

```python
# Python 生成 sed 命令（注意转义）
full_key = "sk-xxx..."  # 从数据库读取
sed_cmd = f'run-as com.termux sed -i "s|  api_key:.*|  api_key: {full_key}|" /data/data/com.termux/files/home/.hermes/config.yaml'
```

注意：sed 替换时要确保缩进保持 YAML 合法（2 空格层级）。

## 实际工作流程：修改 Hermes 的 model 配置（切换到 freeLLMAPI）

场景：把 Hermes 的 base_url 从 New API 切换到 freeLLMAPI，同时换 api_key。

```python
import subprocess

# 1. 从手机读取当前配置
result = subprocess.run(
    ['adb', '-s', '<serial>', 'shell', 'run-as com.termux',
     'cat', '/data/data/com.termux/files/home/.hermes/config.yaml'],
    capture_output=True, text=True
)
lines = result.stdout.split('\n')  # split('\n') 而不是 readlines()，保留最后无换行符

# 2. 找到要改的行并替换（0-indexed）
for i, line in enumerate(lines):
    if 'base_url' in line and ':3000' in line:
        lines[i] = line.replace(':3000', ':3001')
    if 'api_key' in line and lines[i].strip().startswith('api_key:'):
        lines[i] = f'  api_key: freellmapi-d2451bbc0aa4b...'
    if 'default:' in line and 'agnes' in line:
        lines[i] = line.replace('agnes-1.5-flash', 'deepseek-v4-pro')

# 3. 写回本地临时文件
new_content = '\n'.join(lines)
with open('/tmp/huo_new_config.yaml', 'w') as f:
    f.write(new_content)

# 4. 推送到 /sdcard/Download/ 再 copy（adb push 直接到 app 目录会 Permission denied）
subprocess.run(['adb', '-s', '<serial>', 'push',
                '/tmp/huo_new_config.yaml', '/sdcard/Download/huo_config_new.yaml'])
subprocess.run(['adb', '-s', '<serial>', 'shell',
                'run-as com.termux cp /sdcard/Download/huo_config_new.yaml '
                '/data/data/com.termux/files/home/.hermes/config.yaml'])
```

注意：`split('\n')` 而不是 `splitlines()` 或 `readlines()`，因为从 adb shell 的输出可能不以换行符结尾，直接用 `readlines()` 可能丢最后一行。

## 易错点

- `sh -c` 中的 `$` 符号会被外层 shell 解析，需用 `\\$` 转义
- 写在 Python 脚本中的 key 字面不会自动截断，但在终端工具输出时会被 Hermes 自动脱敏显示为 `...`。实际值以 Python 变量中的完整字符串为准
- YAML 缩进：model: / provider: / base_url: / api_key: 都是 2 空格缩进
- `adb pull /data/data/com.termux/files/home/...` 也报 Permission denied，必须通过 `run-as com.termux cat ...` 管道输出到本地文件
- 推送后检查：`head -6` 确认文件完整，不要只看 `echo "done"`
