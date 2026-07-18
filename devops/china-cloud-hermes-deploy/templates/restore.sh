#!/bin/bash
# 夏虫一键恢复 — 新容器上 5 分钟原地复活
# 用法: bash <(curl -sL https://raw.githubusercontent.com/angelife/xia-chong/main/restore.sh)
#
# API KEY 安全: 不从脚本写死 key，从环境变量读
# GITHUB PUSH: 容器没用 SSH key，用 HTTPS + PAT token（见 SKILL.md 的 Git Push 章节）
set -e

echo "=============================="
echo "  夏虫复活脚本"
echo "=============================="
echo ""

# ===== 配置 =====
ZHIPU_API_KEY="${ZHIPU_API_KEY:-}"
if [ -z "$ZHIPU_API_KEY" ]; then
    echo "需要智谱 API Key"
    echo "   ZHIPU_API_KEY=xxx bash restore.sh"
    exit 1
fi

# ===== 1. Hermes 环境 =====
echo "[1/5] 激活 Hermes..."
if conda env list 2>/dev/null | grep -q hermes; then
    source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null
    conda activate hermes
    echo "  OK Hermes 环境已激活"
else
    echo "  创建 Hermes conda 环境..."
    conda create -n hermes python=3.11 -y 2>/dev/null
    source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null
    conda activate hermes
    pip install hermes-agent 2>/dev/null
    echo "  OK Hermes 已安装"
fi

# ===== 2. 配置 Provider =====
echo "[2/5] 配置 Hermes provider..."
hermes config set providers.zhipu.base_url https://open.bigmodel.cn/api/paas/v4/
hermes config set providers.zhipu.api_key "$ZHIPU_API_KEY"
hermes config set providers.zhipu.timeout 120
hermes config set providers.zhipu.max_tokens 8192
hermes config set model.default GLM-4-Flash
hermes config set model.provider zhipu
echo "  OK 智谱 GLM-4-Flash 已配置"

# ===== 3. 设定时备份 =====
echo "[3/5] 设置定时备份..."
BACKUP_SCRIPT=/root/.xia-backup.sh
if [ ! -f "$BACKUP_SCRIPT" ]; then
    curl -sL "https://raw.githubusercontent.com/angelife/xia-chong/main/xia-backup.sh" -o "$BACKUP_SCRIPT"
    chmod +x "$BACKUP_SCRIPT"
fi

if command -v crontab &>/dev/null; then
    (crontab -l 2>/dev/null | grep -v xia-backup
     echo "0 */4 * * * bash $BACKUP_SCRIPT >> /root/.xia-backup.log 2>&1") | crontab -
    echo "  OK 每4小时备份已设置"
else
    echo "  crontab 不可用，需要手动安装或用 sleep 循环替代"
fi

# ===== 4. 验证 =====
echo "[4/5] 验证 Hermes..."
if hermes -z "1+1=" --quiet 2>/dev/null; then
    echo "  OK Hermes 测试通过"
else
    echo "  Hermes 测试失败（检查 key/网络）"
fi

echo ""
echo "=============================="
echo "  夏虫复活 OK"
echo "=============================="
echo "  hermes -z question"
