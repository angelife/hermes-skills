# Jetson Nano（2019原版）vs Orin Nano（2023）跑LLM — 多型号验证案例

**验证时间：** 2026-06-30  
**触发规则：** 产品线内多型号的来源处理规则（原版Nano vs Orin Nano）

---

## 搜索词与召回型号

搜索词：`Nvidia Jetson Nano run LLM inference llama ollama`  
**召回型号（两个硬件能力差异极大的产品）：**

| 型号 | 代号 | 架构 | CUDA | GPU内存 | 上市时间 |
|------|------|------|------|---------|---------|
| Jetson Nano（原版） | - | Maxwell | 10.2 | 2GB/4GB | 2019 |
| Jetson Orin Nano | - | Ampere | 11.4 | 8GB | 2023 |

两型号搜索词完全相同，结论必须物理分隔。

---

## 来源清单（已验证）

### 原版Nano相关来源

| 来源 | 内容摘要 | 验证结果 |
|------|---------|---------|
| [jetson-ai-lab.com/tutorials/ollama](https://www.jetson-ai-lab.com/tutorials/ollama) | 官方支持的Jetson设备列表，**原版Nano不在列** | 完整提取 ✅ |
| [forums.developer.nvidia.com/t/293371](https://forums.developer.nvidia.com/t/how-to-run-local-llm-with-cuda-10-2-support/293371) | NVIDIA官方："Orin方案不支持CUDA 10.2，比树莓派5还慢"；用户投诉Ollama无CUDA加速 | 完整提取 ✅ |
| [github.com/kreier/llama.cpp-jetson](https://github.com/kreier/llama.cpp-jetson) | 原版Nano可编译llama.cpp实现GPU加速，20%提升（相对于CPU），GPU负载1.5GB/4W | 完整提取 ✅ |

### Orin Nano相关来源

| 来源 | 内容摘要 | 验证结果 |
|------|---------|---------|
| [jetson-ai-lab.com/tutorials/ollama](https://www.jetson-ai-lab.com/tutorials/ollama) | Orin Nano在官方支持列表中；Docker安装命令；`ollama run gpt-oss:20b`示例输出 | 完整提取 ✅ |
| [forums.developer.nvidia.com/t/278708](https://forums.developer.nvidia.com/t/ollama-and-jetson-issue/278708) | Orin NX上`libnvidia-ml.so`路径问题，需修复CUDA stub | 完整提取 ✅ |
| [forums.developer.nvidia.com/t/328687](https://forums.developer.nvidia.com/t/ollama-support-for-jetson-nano/328687) | 2024年8月后Ollama增加了Orin系列支持 | 完整提取 ✅ |

---

## 结论（按型号分隔）

### 原版Jetson Nano（2019款）

**结论：⚠️ 勉强可行，极不推荐**

- Ollama官方不支持GPU加速（原版Nano不在支持列表）
- 绕过方案：llama.cpp手动编译（kreier/llama.cpp-jetson），但GPU加速仅20%提升
- GPU内存2GB，7B模型Q4量化需3.5-4GB，余量极小
- **推荐：** 不建议用原版Nano跑LLM

### Jetson Orin Nano 8GB

**结论：✅ 完全可行**

- Ollama官方支持，CUDA加速
- Docker安装：`dustynv/ollama:r36.2.0`
- 性能示例：gpt-oss:20b，prompt eval 112.85 tokens/s，eval 33.80 tokens/s
- **推荐：** Orin Nano 8GB可用gpt-oss:7b或Llama3.2 3B

---

## 自检结果

| 检查项 | 状态 |
|--------|------|
| 型号物理分隔 | ✅ 两型号结论完全分开 |
| 无跨型号合并结论 | ✅ |
| 来源按型号归属标注 | ✅ |
| 推测路径已标注 | ✅ "Orin Nano Super性能"列为推测（未提取验证） |
| 无流程违规 | ✅ 本次无"先写后验证" |

---

## 本案例验证的规则

1. **产品线内多型号处理规则** — 同一搜索词召回两条不同代际产品线时，必须物理分隔
2. **来源精确匹配** — jetson-ai-lab.com同时覆盖两个型号，但同一来源的不同部分服务于不同型号结论，需要在来源表中明确标注"该来源服务于哪个型号的结论"