# -*- coding: utf-8 -*-
"""
东方财富板块资金流实时抓取脚本
- 数据存入 SQLite 数据库（自动建表，永久保存）
- 同时生成 fund_flow_data.json（今日实时，供前端页面读取）
- 收盘后自动导出近5日数据 chart_data_5d.json（供5日连续走势用）
"""

import requests
import json
import re
import time
import os
import sys
import sqlite3
from datetime import datetime, timedelta

# ============ 配置区 ============
FETCH_INTERVAL = 15     # 抓取间隔（秒）

# 数据文件放在 exe 同目录下（打包后也如此）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(APP_DIR, "fund_flow.db")
TODAY_JSON = os.path.join(APP_DIR, "fund_flow_data.json")
FIVE_DAY_JSON = os.path.join(APP_DIR, "chart_data_5d.json")
# ================================

HEADERS = {
    "Referer": "https://data.eastmoney.com/bkzj/gn.html",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# ============ 数据库操作 ============

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS board_fund (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        time_point TEXT NOT NULL,
        board_name TEXT NOT NULL,
        main_net REAL,
        super_net REAL,
        big_net REAL,
        mid_net REAL,
        small_net REAL,
        UNIQUE(trade_date, time_point, board_name)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS market_total (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT NOT NULL,
        time_point TEXT NOT NULL,
        main_net REAL,
        super_net REAL,
        big_net REAL,
        mid_net REAL,
        small_net REAL,
        UNIQUE(trade_date, time_point)
    )''')
    conn.commit()
    conn.close()


def save_to_db(trade_date, time_point, boards_data, market_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    rows = []
    for name, info in boards_data.items():
        rows.append((
            trade_date, time_point, name,
            info.get("主力", 0), info.get("超大单", 0),
            info.get("大单", 0), info.get("中单", 0), info.get("小单", 0)
        ))
    c.executemany('''INSERT OR REPLACE INTO board_fund
        (trade_date, time_point, board_name, main_net, super_net, big_net, mid_net, small_net)
        VALUES (?,?,?,?,?,?,?,?)''', rows)

    if market_data:
        c.execute('''INSERT OR REPLACE INTO market_total
            (trade_date, time_point, main_net, super_net, big_net, mid_net, small_net)
            VALUES (?,?,?,?,?,?,?)''', (
            trade_date, time_point,
            market_data.get("主力", 0), market_data.get("超大单", 0),
            market_data.get("大单", 0), market_data.get("中单", 0), market_data.get("小单", 0)
        ))
    conn.commit()
    conn.close()


def export_today_json(trade_date):
    """从数据库导出今日数据为JSON"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT DISTINCT time_point FROM board_fund WHERE trade_date=? ORDER BY time_point", (trade_date,))
    timestamps = [r[0] for r in c.fetchall()]

    c.execute("SELECT DISTINCT board_name FROM board_fund WHERE trade_date=?", (trade_date,))
    board_names = [r[0] for r in c.fetchall()]

    boards = {}
    for name in board_names:
        c.execute("SELECT main_net,super_net,big_net,mid_net,small_net FROM board_fund WHERE trade_date=? AND board_name=? ORDER BY time_point", (trade_date, name))
        rows = c.fetchall()
        boards[name] = {
            "主力": [r[0] for r in rows],
            "超大单": [r[1] for r in rows],
            "大单": [r[2] for r in rows],
            "中单": [r[3] for r in rows],
            "小单": [r[4] for r in rows],
        }

    c.execute("SELECT main_net,super_net,big_net,mid_net,small_net FROM market_total WHERE trade_date=? ORDER BY time_point", (trade_date,))
    market_rows = c.fetchall()
    market_total = [{"主力": r[0], "超大单": r[1], "大单": r[2], "中单": r[3], "小单": r[4]} for r in market_rows]

    conn.close()

    result = {"date": trade_date, "timestamps": timestamps, "boards": boards, "market_total": market_total}
    with open(TODAY_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return len(timestamps), len(board_names)


def export_5day_json():
    """导出最近5个交易日的连续数据"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT DISTINCT trade_date FROM board_fund ORDER BY trade_date DESC LIMIT 5")
    dates = [r[0] for r in c.fetchall()]
    dates.sort()

    if not dates:
        conn.close()
        return

    timestamps = []
    for d in dates:
        c.execute("SELECT DISTINCT time_point FROM board_fund WHERE trade_date=? ORDER BY time_point", (d,))
        times = [r[0] for r in c.fetchall()]
        for t in times:
            timestamps.append(f"{d[5:]} {t[:5]}")

    placeholders = ",".join("?" * len(dates))
    c.execute(f"SELECT DISTINCT board_name FROM board_fund WHERE trade_date IN ({placeholders})", dates)
    board_names = [r[0] for r in c.fetchall()]

    boards = {}
    for name in board_names:
        series = []
        for d in dates:
            c.execute("SELECT main_net,super_net,big_net,mid_net,small_net FROM board_fund WHERE trade_date=? AND board_name=? ORDER BY time_point", (d, name))
            rows = c.fetchall()
            for r in rows:
                series.append({
                    "主力": r[0], "超大单": r[1], "大单": r[2], "中单": r[3], "小单": r[4]
                })

        boards[name] = {
            "主力": [s["主力"] for s in series],
            "超大单": [s["超大单"] for s in series],
            "大单": [s["大单"] for s in series],
            "中单": [s["中单"] for s in series],
            "小单": [s["小单"] for s in series],
        }

    market_total = []
    for d in dates:
        c.execute("SELECT main_net,super_net,big_net,mid_net,small_net FROM market_total WHERE trade_date=? ORDER BY time_point", (d,))
        for r in c.fetchall():
            market_total.append({"主力": r[0], "超大单": r[1], "大单": r[2], "中单": r[3], "小单": r[4]})

    conn.close()

    result = {
        "mode": "5day",
        "dates": dates,
        "timestamps": timestamps,
        "boards": boards,
        "market_total": market_total
    }
    with open(FIVE_DAY_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[导出5日数据] {len(dates)}个交易日, {len(timestamps)}个时间点, {len(board_names)}个板块")


# ============ 数据抓取 ============

def fetch_board_fund_flow():
    """分页抓取全部概念板块资金流"""
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    all_result = {}
    page = 1
    total = None

    while True:
        params = {
            "cb": "jQuery", "fid": "f62", "po": 1, "pz": 100, "pn": page,
            "np": 1, "fltt": 2, "invt": 2, "fs": "m:90 t:3",
            "fields": "f12,f14,f62,f184,f66,f72,f78,f84"
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            m = re.search(r'jQuery\((.*)\)', r.text)
            data = json.loads(m.group(1))
            diff = data["data"]["diff"]
            if not diff:
                break
            for item in diff:
                name = item["f14"]
                all_result[name] = {
                    "主力": round(item["f62"] / 1e8, 2),
                    "主力占比": item.get("f184", 0),
                    "超大单": round(item["f66"] / 1e8, 2),
                    "大单": round(item["f72"] / 1e8, 2),
                    "中单": round(item["f78"] / 1e8, 2),
                    "小单": round(item["f84"] / 1e8, 2),
                }
            if total is None:
                total = data["data"]["total"]
            if len(all_result) >= total:
                break
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"[抓取失败 第{page}页] {e}")
            break

    return all_result if all_result else None


def fetch_market_total():
    """抓取大盘整体资金流"""
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "cb": "jQuery", "fltt": 2, "invt": 2,
        "fields": "f62,f66,f72,f78,f84,f184",
        "secids": "1.000001,0.399001"
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        m = re.search(r'jQuery\((.*)\)', r.text)
        data = json.loads(m.group(1))
        items = data["data"]["diff"]
        total = {"主力": 0, "超大单": 0, "大单": 0, "中单": 0, "小单": 0}
        for it in items:
            total["主力"] += it.get("f62", 0) / 1e8
            total["超大单"] += it.get("f66", 0) / 1e8
            total["大单"] += it.get("f72", 0) / 1e8
            total["中单"] += it.get("f78", 0) / 1e8
            total["小单"] += it.get("f84", 0) / 1e8
        return {k: round(v, 2) for k, v in total.items()}
    except Exception as e:
        print(f"[大盘数据抓取失败] {e}")
        return None


def is_trading_time():
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.hour * 100 + now.minute
    return (925 <= t <= 1132) or (1258 <= t <= 1505)


def main():
    print("=" * 50)
    print("板块资金流实时监控（数据库版）")
    print(f"数据库: {DB_FILE}")
    print(f"抓取间隔: {FETCH_INTERVAL}秒")
    print("=" * 50)

    init_db()
    last_export_date = None

    while True:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        trade_date = now.strftime("%Y-%m-%d")

        if not is_trading_time():
            if last_export_date != trade_date and os.path.exists(DB_FILE):
                try:
                    export_5day_json()
                    last_export_date = trade_date
                except:
                    pass
            print(f"[{time_str}] 非交易时段，等待中...")
            time.sleep(60)
            continue

        all_boards = fetch_board_fund_flow()
        market = fetch_market_total()

        if all_boards:
            save_to_db(trade_date, time_str, all_boards, market)
            n_points, n_boards = export_today_json(trade_date)
            print(f"[{time_str}] 已存库 {len(all_boards)} 板块 | 今日累计 {n_points} 个时间点")

            sorted_all = sorted(all_boards.items(), key=lambda x: x[1]["主力"], reverse=True)
            print("  流入TOP3:", " | ".join([f"{n}:{i['主力']:+.1f}亿" for n, i in sorted_all[:3]]))
            print("  流出TOP3:", " | ".join([f"{n}:{i['主力']:+.1f}亿" for n, i in sorted_all[-3:]]))

            if now.hour >= 15 and last_export_date != trade_date:
                export_5day_json()
                last_export_date = trade_date

        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main()
