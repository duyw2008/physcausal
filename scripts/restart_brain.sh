#!/bin/bash
# 费曼脑重启 — 清pycache + 停旧 + 启新
set -e

echo "=== 1. 清 pycache ==="
rm -rf /home/duyw/Agent/physcausal/meta_cognition/__pycache__
echo "done"

echo "=== 2. 停脑 ==="
systemctl --user stop feynman-brain 2>/dev/null || true
# 确保进程真死了
BRAIN_PID=$(pgrep -f '/usr/bin/python3.*run_evo' 2>/dev/null || true)
if [ -n "$BRAIN_PID" ]; then
    kill -TERM $BRAIN_PID 2>/dev/null || true
    sleep 5
fi
echo "done"

echo "=== 3. 启脑 ==="
systemd-run --user --unit=feynman-brain --same-dir --collect \
  bash -c 'cd /home/duyw/Agent/physcausal && exec /usr/bin/python3 -u run_evo.py >> data/evo_output.log 2>&1'
echo "done"

sleep 2
echo "=== 4. 验证 ==="
pgrep -f '/usr/bin/python3.*run_evo' && echo "RUNNING" || echo "检查日志: tail ~/Agent/physcausal/data/evo_output.log"
