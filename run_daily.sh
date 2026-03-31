#!/bin/bash
# 股票监控定时任务 - 直接输出到文件，用户自行查看

cd /Users/ricardo.chen/.qclaw/workspace/stock-monitor

# 获取当前日期
DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H:%M")

# 执行脚本并保存结果
python3 fetch_stocks.py > "reports/report_${DATE}_${TIME}.txt" 2>&1

# 同时更新最新报告
python3 fetch_stocks.py > "reports/latest.txt" 2>&1

echo "Report saved to reports/report_${DATE}_${TIME}.txt"
