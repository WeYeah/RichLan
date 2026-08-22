#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞龙股份 & 英维克 每日更新脚本
- 拉取腾讯免费行情（实时快照 + 前复权日K线）
- 计算技术因子与综合信心指数
- 生成 data/snapshot.json（供前端看板读取）
- 输出每日简报文本（供 GitHub Actions 推送到 webhook）

仅依赖 Python 标准库，无第三方依赖，可在 GitHub Actions ubuntu 直接运行。
"""

import json
import urllib.request
import datetime
import os
import sys

# 标的配置
STOCKS = {
    "yk": {"name": "英维克", "code": "002837", "sec": "sz002837"},
    "fl": {"name": "飞龙股份", "code": "002536", "sec": "sz002536"},
}

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def http_get(url, encoding="utf-8"):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=20).read().decode(encoding, "ignore")


def fetch_quote(sec):
    """腾讯实时行情，返回解析后的关键字段"""
    try:
        raw = http_get("https://qt.gtimg.cn/q=%s" % sec, encoding="gbk")
    except Exception as e:
        print("  [warn] quote fetch fail: %s" % e)
        return None
    p = raw.split("~")
    if len(p) < 50:
        return None

    def f(i):
        try:
            v = float(p[i])
            return None if v == 0 and i in (44, 45) else v
        except Exception:
            return None

    return {
        "price": f(3), "prev": f(4), "open": f(5),
        "change": f(31), "pct": f(32),
        "high": f(33), "low": f(34),
        "vol": f(36), "amount": (f(37) / 10000.0 if f(37) else None),
        "turn": f(38), "pe": f(39), "pb": f(46),
        "mktcap": f(45), "floatcap": f(44),
        "up_limit": f(47), "dn_limit": f(48), "ratio": f(49),
    }


def fetch_kline(sec, n=90):
    """腾讯前复权日K线，[date, open, close, high, low, volume]"""
    try:
        data = json.loads(http_get(
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=%s,day,,,%d,qfq" % (sec, n)))
        d = data["data"][sec]
        k = d.get("qfqday") or d.get("day") or []
    except Exception as e:
        print("  [warn] kline fetch fail: %s" % e)
        return []
    out = []
    for r in k:
        try:
            out.append([r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])])
        except Exception:
            continue
    return out


def ma(closes, n):
    if len(closes) < n:
        return None
    return round(sum(closes[-n:]) / n, 2)


def calc_confidence(kline, quote):
    """综合信心指数（0-100），由 4 个可解释因子加权合成"""
    closes = [r[2] for r in kline]
    if len(closes) < 25:
        return {"score": 50, "trend": "flat", "factors": {}, "note": "数据不足"}

    # 因子1：近20日动量（25分）
    chg20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) > 21 else 0
    if chg20 >= 20: m = 25
    elif chg20 >= 12: m = 22
    elif chg20 >= 5: m = 19
    elif chg20 >= 0: m = 15
    elif chg20 >= -8: m = 10
    elif chg20 >= -15: m = 6
    else: m = 2

    # 因子2：均线结构（25分）
    ma5 = ma(closes, 5)
    ma20 = ma(closes, 20)
    a = 0
    if ma20 and closes[-1] >= ma20:
        a += 13
    if ma5 and ma20 and ma5 >= ma20:
        a += 12

    # 因子3：量能活跃（25分）
    turn = quote.get("turn") or 0
    if turn >= 8: v = 25
    elif turn >= 5: v = 22
    elif turn >= 3: v = 18
    elif turn >= 2: v = 14
    elif turn >= 1: v = 10
    else: v = 6

    # 因子4：估值安全（25分）
    pe = quote.get("pe") or 200
    if pe <= 30: e = 25
    elif pe <= 50: e = 20
    elif pe <= 80: e = 15
    elif pe <= 120: e = 10
    elif pe <= 200: e = 6
    else: e = 3

    score = m + a + v + e
    score = max(0, min(100, score))
    return {
        "score": score,
        "factors": {
            "momentum": {"label": "近20日动量", "score": m, "value": round(chg20, 1)},
            "ma": {"label": "均线结构", "score": a, "value": "站上MA20" if a >= 13 else "跌破MA20"},
            "volume": {"label": "量能活跃", "score": v, "value": round(turn, 1)},
            "valuation": {"label": "估值安全", "score": e, "value": round(pe, 1)},
        },
    }


def level(score):
    if score >= 70: return "偏强"
    if score >= 55: return "中性偏多"
    if score >= 45: return "中性"
    if score >= 30: return "中性偏弱"
    return "偏弱"


def load_prev(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def main():
    repo_dir = os.getcwd()
    out_path = os.path.join(repo_dir, "data", "snapshot.json")

    prev = load_prev(out_path)
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")

    result = {"updated": now_str, "updated_date": now.strftime("%Y-%m-%d"),
              "note": "由 GitHub Actions 每日自动更新", "stocks": {}}

    brief_lines = ["# 飞龙股份 & 英维克 · 每日监控简报", "",
                   "更新：%s" % now_str, ""]

    for key, cfg in STOCKS.items():
        print("[%s] %s" % (key, cfg["name"]))
        quote = fetch_quote(cfg["sec"])
        kline = fetch_kline(cfg["sec"], 90)
        conf = calc_confidence(kline, quote or {})
        trend = "flat"
        if prev and key in prev.get("stocks", {}):
            pscore = prev["stocks"][key].get("confidence", {}).get("score")
            if pscore is not None:
                if conf["score"] > pscore + 3: trend = "up"
                elif conf["score"] < pscore - 3: trend = "down"
        conf["trend"] = trend
        conf["level"] = level(conf["score"])

        result["stocks"][key] = {
            "name": cfg["name"], "code": cfg["code"],
            "quote": quote, "kline": kline, "confidence": conf,
        }

        if quote and quote.get("price"):
            brief_lines.append("## %s（%s）" % (cfg["name"], cfg["code"]))
            brief_lines.append("- 现价：%.2f（%+.2f / %+.2f%%）" % (
                quote["price"], quote.get("change") or 0, quote.get("pct") or 0))
            brief_lines.append("- PE(TTM) %.1f · PB %.2f · 总市值 %.1f 亿" % (
                quote.get("pe") or 0, quote.get("pb") or 0, quote.get("mktcap") or 0))
            brief_lines.append("- 信心指数：%d（%s，较前值%s）" % (
                conf["score"], conf["level"],
                {"up": "回升", "down": "回落", "flat": "持平"}.get(trend)))
            brief_lines.append("")
        else:
            brief_lines.append("## %s：行情获取失败" % cfg["name"])
            brief_lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("written:", out_path)
    print("=" * 40)
    print("\n".join(brief_lines))

    # 输出简报到文件供 workflow 读取
    brief_path = os.path.join(repo_dir, "data", "brief.md")
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write("\n".join(brief_lines))
    print("written:", brief_path)


if __name__ == "__main__":
    main()
