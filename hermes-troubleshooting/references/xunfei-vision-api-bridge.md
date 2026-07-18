# Xunfei Vision API Bridge

## Purpose

When the active Hermes model (e.g. deepseek-v4-flash-free) does NOT support multimodal/vision inputs, you can bridge to the configured xunfei (讯飞) API which hosts the vision-capable `xopqwen36v35b` model.

## Prerequisites

- `XUNFEI_API_KEY` set in `~/.hermes/.env`
- Image file available at a known path (usually `~/.hermes/image_cache/img_*.jpg`)

## Recipe

### One-shot from Terminal (curl)

```bash
source ~/.hermes/.env
BASE64_IMG=$(base64 -i /path/to/image.jpg)
curl -s --max-time 35 https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions \
  -H "Authorization: Bearer $XUNFEI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "xopqwen36v35b",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "请详细描述这张图片的内容，包括所有文字信息。用中文回答。"},
          {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,'"$BASE64_IMG"'"}}
        ]
      }
    ],
    "max_tokens": 800
  }' | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['choices'][0]['message']['content'])"
```

### Using a Python script (more reliable for complex queries)

Save as `scripts/xunfei-vision.py` and invoke via:

```bash
source ~/.hermes/.env && python3 scripts/xunfei-vision.py /path/to/image.jpg "your prompt"
```

```python
#!/usr/bin/env python3
import base64, json, os, sys, urllib.request, urllib.error

api_key = os.environ.get('XUNFEI_API_KEY', '')
if not api_key:
    print("ERROR: XUNFEI_API_KEY not set in environment")
    sys.exit(1)

image_path = sys.argv[1] if len(sys.argv) > 1 else None
if not image_path or not os.path.exists(image_path):
    print(f"ERROR: image not found: {image_path}")
    sys.exit(1)

with open(image_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

prompt = sys.argv[2] if len(sys.argv) > 2 else "请详细描述这张图片的内容，包括所有文字信息。用中文回答。"

url = 'https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}
payload = json.dumps({
    'model': 'xopqwen36v35b',
    'messages': [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
        ]
    }],
    'max_tokens': 800
}).encode()

req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req, timeout=35) as resp:
        result = json.loads(resp.read())
        print(result['choices'][0]['message']['content'])
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code} {e.reason}')
    print(e.read().decode())
except Exception as e:
    print(f'Error: {e}')
```

## Known Working Configuration

- **Endpoint**: `https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions`
- **Model**: `xopqwen36v35b`
- **Auth**: Bearer token (OpenAI-compatible)
- **Format**: OpenAI-style chat completion with `image_url` content type
- **Environment**: `XUNFEI_API_KEY` in `~/.hermes/.env`

## Limitations

- Large images (>20MB) may hit timeout or payload limits
- Only tested with JPEG format
- The xunfei API endpoint has its own rate limits
- Image description quality depends on the xopqwen36v35b model capabilities
