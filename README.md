# Stock Monitor

一个用于跟踪股票现价、买卖点距离和股息率的轻量脚本项目。支持 A 股、港股、美股，并输出可直接阅读的日报表格。

## 功能说明

- 批量获取股票价格（按市场分源请求）
- 计算距买点、距卖点百分比
- 计算股息率并按股息率排序展示
- 输出到终端或保存为报告文件

## 项目结构

- `fetch_stocks.py`：主脚本，读取配置并生成日报
- `stocks.json`：股票池与买卖点配置
- `run_daily.sh`：定时任务脚本，输出日报文件到 `reports/`
- `reports/`：报告输出目录（运行后自动创建）

## 环境要求

- macOS / Linux
- `python3`
- `curl`

## 快速开始

在项目根目录执行：

```bash
python3 ./fetch_stocks.py
```

## 配置股票池

编辑 `stocks.json` 中的 `stocks` 列表，常见字段示例：

```json
{
  "name": "招商银行",
  "market": "sh",
  "code": "600036",
  "buy": 35.0,
  "sell": 46.0,
  "dividend": 1.972
}
```

字段说明：

- `market`：`sh` / `sz` / `hk` / `us`
- `code`：交易代码（港股按现有格式填写）
- `buy`：买点价格
- `sell`：卖点价格
- `dividend`：预计每股分红（可选）

## 生成日报文件

```bash
bash ./run_daily.sh
```

执行后会生成：

- `reports/latest.txt`
- `reports/report_YYYY-MM-DD_HH:MM.txt`

## 定时执行（可选）

可通过 `crontab -e` 添加定时任务，例如每个交易日 9:30 和 15:30 执行：

```cron
30 9 * * 1-5 cd /path/to/stock-monitor && bash ./run_daily.sh
30 15 * * 1-5 cd /path/to/stock-monitor && bash ./run_daily.sh
```

请将 `/path/to/stock-monitor` 替换为你本机实际目录。
