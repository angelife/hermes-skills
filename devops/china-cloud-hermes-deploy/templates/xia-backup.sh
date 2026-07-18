#!/bin/bash
# 夏虫备份脚本 — 每 4 小时推配置到 GitHub
# 用法: bash /root/.xia-backup.sh
# cron: (crontab -l; echo "0 */4 * * * bash /root/.xia-backup.sh >> /root/.xia-backup.log 2>&1") | crontab -
#
# 首次运行需要先设置 remote URL（含 PAT token）:
#   cd /root/.xia-backup && git remote set-url origin https://user:TOKEN@github.com/angelife/xia-chong.git
set -e

BACKUP_DIR="/root/.xia-backup"
DATE=$(date '+%Y%m%d_%H%M%S')
LOG="/root/.xia-backup.log"

echo "[$DATE] === 备份开始 ===" >> "$LOG"

mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"

# 初始化仓库
if [ ! -d ".git" ]; then
    git init
    git branch -m master main
fi

# Hermes 配置（脱敏 API Key）
cp /root/.hermes/config.yaml . 2>/dev/null || true
sed -i 's/api_key: .*/api_key: REDACTED/' config.yaml 2>/dev/null || true

# 自定义脚本
cp /root/*.sh /root/*.py . 2>/dev/null || true

# 备份 cron
crontab -l > crontab.txt 2>/dev/null || echo "# no crontab" > crontab.txt

# 版本信息
{
    echo "backup: $DATE"
    echo "hermes: $(hermes --version 2>/dev/null || echo unknown)"
    echo "host: $(hostname 2>/dev/null || echo unknown)"
} > info.txt

git add -A 2>/dev/null
git commit -m "backup $DATE" 2>/dev/null || true
git push origin main 2>/dev/null && echo "  OK 推送成功" >> "$LOG" \
    || echo "  推送失败（检查 remote URL 或网络）" >> "$LOG"

echo "[$DATE] === 备份结束 ===" >> "$LOG"
