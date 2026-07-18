# Hindsight Cloud Setup Record

基于 2026-06-20 对话配置记录。

## 环境

- Hermes Agent (deepseek-v4-flash-free / opencode-zen)
- macOS 15.7
- Hermes 工作目录: `/Users/macos/.hermes`

## 步骤摘要

1. 注册获取 API Key: https://ui.hindsight.vectorize.io
2. 设置 provider: `hermes config set memory.provider hindsight`
3. 写入环境变量: `echo 'HINDSIGHT_API_KEY=...' >> ~/.hermes/.env`
4. 安装客户端: `uv pip install "hindsight-client>=0.4.22"`
5. 测试验证

## Bank 配置

默认 `bank_id: hermes` 已存在，配置包含：

```json
{
  "enable_observations": true,
  "enable_auto_consolidation": true,
  "retain_extraction_mode": "concise",
  "recall_budget_function": "fixed",
  "recall_budget_fixed_low": 100,
  "recall_budget_fixed_mid": 300,
  "recall_budget_fixed_high": 1000,
  "recall_budget_min": 20,
  "recall_budget_max": 2000
}
```

## 验证通过的 API 操作

### retain
```python
h.retain(bank_id="hermes", content="...", context="...")
# 返回: success=True items_count=1 usage=TokenUsage(...)
```

### recall
```python
resp = h.recall(bank_id="hermes", query="...", budget="low")
for r in resp.results:
    print(r.text)  # 注意是 .text 不是 .content
```

### reflect
```python
resp = h.reflect(bank_id="hermes", query="...", budget="low")
print(resp.text)  # LLM 综合后的文本
```

### 查看 bank config
```python
h.get_bank_config("hermes")
```

### 可用方法
```python
dir(h)  # 查看所有方法: retain, recall, reflect, list_memories, banks, directives, etc.
```

## 版本

- hindsight-client: 0.8.3
- Cloud API: 0.8.2
- features: observations, mcp, bank_config_api, file_upload_api, document_export_api, document_import_api

## 多 Agent 共享

- 所有 agent 用相同 `HINDSIGHT_API_KEY` + `bank_id: hermes` → 共享记忆池
- 用 `bank_id_template: "hermes-{profile}"` 可隔离
- 金木水火土群组适用共享池模式（同一 bank_id）
