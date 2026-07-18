#!/usr/bin/env python3
"""
Triple Model Analysis — 三模型并行审稿模板
用法: python3 run_triple_analysis.py "文章摘要内容"

依赖: python3 标准库（urllib, json, time）
认证: 从 ~/.hermes/.env 读取 NVIDIA_API_KEY，从环境变量或硬编码读取其他 key
"""
import urllib.request, urllib.error, json, time, sys, os

# ========== 配置区 ==========
ZHIHU_KEY = os.environ.get('ZHIHU_API_KEY', 'f62bd8bc4422aad0a64b90f48cb56f2d5770831b')
XF_KEY = '074bcc86c4939819c952862a180f1929:YTA4ZTczYjE4YTcxYzQ4NjExMmFjNzNh'
NV_KEY = None

# 从 .env 读 NVIDIA key
env_path = os.path.expanduser('~/.hermes/.env')
if os.path.exists(env_path):
    for line in open(env_path):
        if 'NVIDIA' in line and ('API' in line or 'KEY' in line):
            NV_KEY = line.split('=', 1)[1].strip()
            break

# ========== 文章摘要 ==========
if len(sys.argv) < 2:
    print("用法: python3 run_triple_analysis.py '文章摘要内容'")
    sys.exit(1)

ARTICLE_SUMMARY = sys.argv[1]

PROMPT = f"""你是技术审稿人。请分析这篇文章：①核心观点与价值 ②亮点 ③局限/风险 每点2-3句话，简洁有力。

文章：
{ARTICLE_SUMMARY}"""

# ========== 模型定义 ==========
MODELS = [
    ("讯飞", "xopqwen36v35b", "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",
     lambda k: {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}),
    ("NVIDIA", "meta/llama-3.1-8b-instruct", "https://integrate.api.nvidia.com/v1/chat/completions",
     lambda k: {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}),
]

def call_model(name, model, url, make_headers, key):
    try:
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 350}).encode()
        req = urllib.request.Request(url, data=body, headers=make_headers(key))
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())['choices'][0]['message']['content']
    except Exception as e:
        return f"ERROR: {e}"

# ========== 执行 ==========
TS = str(int(time.time()))

for name, model, url, make_headers in MODELS:
    key = NV_KEY if name == "NVIDIA" else XF_KEY
    result = call_model(name, model, url, make_headers, key)
    print(f"\n{'='*40}")
    print(f"【{name}】")
    print(result)

# 知乎（特殊认证）
def call_zhihu():
    try:
        body = json.dumps({"model": "zhida-thinking-1p5", "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 350}).encode()
        req = urllib.request.Request(
            "https://developer.zhihu.com/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {ZHIHU_KEY}", "X-Request-Timestamp": TS, "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())['choices'][0]['message']['content']
    except Exception as e:
        return f"ERROR: {e}"

print(f"\n{'='*40}")
print("【知乎】")
print(call_zhihu())