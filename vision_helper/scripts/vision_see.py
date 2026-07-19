#!/usr/bin/env python3
"""Vision Helper: 用 OpenRouter 免费多模态模型识别图片，输出文字描述。

用法: python3 vision_see.py <图片路径> ["你的问题"]
木同学本体模型不变，此脚本仅作外部"眼睛"。
"""
import sys, os, json, base64, urllib.request

def get_key():
    p = "/tmp/.orkey"
    if os.path.exists(p):
        return open(p).read().strip()
    return os.environ.get("OPENROUTER_API_KEY", "")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 vision_see.py <图片路径> [问题]")
        sys.exit(1)
    img = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else \
        "用中文详细描述这张图片的全部内容，包括所有可见文字、数字、配置项、按钮、错误信息或界面元素。"
    if not os.path.exists(img):
        print(f"图片不存在: {img}")
        sys.exit(1)

    key = get_key()
    if not key:
        print("NO KEY: 把 OpenRouter key 存到 /tmp/.orkey 或设 OPENROUTER_API_KEY")
        sys.exit(1)

    b64 = base64.b64encode(open(img, "rb").read()).decode()
    MODELS = [
        "google/gemini-3.1-flash-lite",
        "google/gemini-flash-1.5",
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-3.1-flash-image",
    ]
    last = ""
    for mdl in MODELS:
        payload = {
            "model": mdl,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            "max_tokens": 1000,
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                resp = json.load(r)
                print(resp["choices"][0]["message"]["content"])
                return
        except Exception as e:
            last = f"{mdl}: {e}"
            try:
                last += " | " + e.read().decode()[:200]
            except:
                pass
    print("ALL FAILED:", last)

if __name__ == "__main__":
    main()
