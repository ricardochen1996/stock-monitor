#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票监控脚本 - 获取现价并计算距买点/卖点百分比
支持 A股(sh/sz)、港股(hk)、美股(us)
- A股/美股：新浪财经
- 港股：东方财富（更实时）
"""

import json
import subprocess
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STOCKS_FILE = BASE_DIR / "stocks.json"

def fetch_sina_batch(symbols):
    """新浪财经批量获取 A股/美股，返回 {symbol: price}"""
    if not symbols:
        return {}
    joined = ",".join(symbols)
    url = f"https://hq.sinajs.cn/list={joined}"
    cmd = ["curl", "-s", "--max-time", "15",
           "-H", "Referer: https://finance.sina.com.cn",
           "-H", "User-Agent: Mozilla/5.0", url]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=20)
        raw = result.stdout.decode("gbk", errors="replace")
    except Exception:
        return {}

    prices = {}
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or '"' not in line:
            continue
        try:
            sym_part = line.split("hq_str_")[1].split("=")[0]
            data_str = line.split('"')[1]
        except IndexError:
            continue
        if not data_str:
            continue
        parts = data_str.split(",")
        try:
            if sym_part.startswith("sh") or sym_part.startswith("sz"):
                # A股: index 3 = 现价
                if len(parts) > 3 and parts[3]:
                    v = float(parts[3])
                    if v > 0:
                        prices[sym_part] = v
            elif sym_part.startswith("gb_"):
                # 美股: index 1 = 现价
                if len(parts) > 1 and parts[1]:
                    v = float(parts[1])
                    if v > 0:
                        prices[sym_part] = v
        except (ValueError, IndexError):
            continue
    return prices


def fetch_eastmoney_hk_batch(hk_stocks):
    """腾讯财经批量获取港股，返回 {symbol: price}"""
    if not hk_stocks:
        return {}
    # 构建 r_hkXXXXX 列表
    sym_list = list(hk_stocks.keys())  # hkXXXXX
    prices = {}
    batch_size = 30
    for i in range(0, len(sym_list), batch_size):
        batch = sym_list[i:i+batch_size]
        # 腾讯接口格式: r_hk01919,r_hk00700,...
        query = ",".join([f"r_{sym}" for sym in batch])
        url = f"https://qt.gtimg.cn/q={query}"
        cmd = ["curl", "-s", "--max-time", "15", url]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=20)
            raw = result.stdout.decode("gbk", errors="replace")
            for line in raw.strip().split(";"):
                line = line.strip()
                if not line or '"' not in line:
                    continue
                # 格式: v_r_hkXXXXX="100~名称~代码~现价~..."
                try:
                    sym_key = line.split("v_r_")[1].split("=")[0]  # hkXXXXX
                    data_str = line.split('"')[1]
                    parts = data_str.split("~")
                    if len(parts) > 3 and parts[3]:
                        price = float(parts[3])
                        if price > 0 and sym_key in hk_stocks:
                            prices[sym_key] = price
                except (IndexError, ValueError):
                    continue
        except Exception:
            pass
        if i + batch_size < len(sym_list):
            time.sleep(0.3)
    return prices


def pct(current, target):
    if not target or target == 0:
        return None
    return (current - target) / target * 100


def signal_tag(dist_buy, dist_sell):
    if dist_buy is None or dist_sell is None:
        return "❓"
    if dist_buy <= 0:
        return "🟢 可买入"
    if dist_sell >= 0:
        return "🔴 可卖出"
    return "⚪ 观望"


def run():
    with open(STOCKS_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    stocks = config["stocks"]

    # 按市场分组
    sina_symbols = {}   # sh/sz/us -> symbol
    hk_stocks    = {}   # hk -> {sym: stock_info}

    for s in stocks:
        market = s["market"]
        code   = s["code"]
        if market == "sh":
            sym = f"sh{code}"
        elif market == "sz":
            sym = f"sz{code}"
        elif market == "us":
            sym = f"gb_{code.lower()}"
        elif market == "hk":
            sym = f"hk{code}"
            hk_stocks[sym] = s
            continue
        else:
            continue
        sina_symbols[sym] = s

    # 获取 A股/美股（新浪）
    price_map = {}
    all_sina = list(sina_symbols.keys())
    for i in range(0, len(all_sina), 30):
        batch = all_sina[i:i+30]
        prices = fetch_sina_batch(batch)
        price_map.update(prices)
        if i + 30 < len(all_sina):
            time.sleep(0.3)

    # 获取港股（东方财富批量）
    hk_prices = fetch_eastmoney_hk_batch(hk_stocks)
    # 对东方财富获取失败的港股，用新浪昨收价兜底
    failed_hk = {sym: s for sym, s in hk_stocks.items() if sym not in hk_prices}
    if failed_hk:
        sina_hk_prices = fetch_sina_batch(list(failed_hk.keys()))
        hk_prices.update(sina_hk_prices)
    price_map.update(hk_prices)

    # 合并所有股票
    all_stocks = {**sina_symbols, **hk_stocks}

    # 计算结果
    results = []
    for sym, s in all_stocks.items():
        price    = price_map.get(sym)
        buy      = s["buy"]
        sell     = s["sell"]
        db       = pct(price, buy)  if price else None
        ds       = pct(price, sell) if price else None
        dividend = s.get("dividend", 0)
        dy       = (dividend / price * 100) if price and price > 0 and dividend else None
        results.append({
            "name": s["name"], "price": price,
            "dividend": dividend, "buy": buy, "sell": sell,
            "dist_buy": db, "dist_sell": ds, "dy": dy
        })

    # 按股息率从高到低排序
    results.sort(key=lambda r: r["dy"] if r["dy"] is not None else -1, reverse=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📊 股票监控日报 · {now}\n\n"]
    lines.append("| 股票名称 | 现价 | 预计分红 | 股息率 | 买点 | 卖点 | 距买点 | 距卖点 | 状态 |")
    lines.append("|---------|------|----------|--------|------|------|--------|--------|------|")

    failed = []
    for r in results:
        name = r["name"]
        if r["price"] is None:
            failed.append(name)
            lines.append(f"| {name:<18} | 获取失败 | - | - | - | - | - | - | ❓ |")
            continue
        price_s = f"{r['price']:.2f}"
        div_s   = f"{r['dividend']:.2f}" if r['dividend'] else "-"
        dy_s    = f"{r['dy']:.2f}%" if r['dy'] is not None else "N/A"
        buy_s   = f"{r['buy']:.2f}"
        sell_s  = f"{r['sell']:.2f}"
        db_s    = f"{r['dist_buy']:+.2f}%"  if r['dist_buy']  is not None else "N/A"
        ds_s    = f"{r['dist_sell']:+.2f}%" if r['dist_sell'] is not None else "N/A"
        sig     = signal_tag(r['dist_buy'], r['dist_sell'])
        lines.append(f"| {name:<18} | {price_s:>8} | {div_s:>8} | {dy_s:>7} | {buy_s:>7} | {sell_s:>7} | {db_s:>9} | {ds_s:>9} | {sig} |")

    if failed:
        lines.append(f"\n⚠️ 价格获取失败：{', '.join(failed)}")

    report = "\n".join(lines)
    print(report)
    return report

if __name__ == "__main__":
    run()
