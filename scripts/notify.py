#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送每日简报到已配置的通知渠道（均通过环境变量/Secrets 传入，未配置则跳过）。
支持：企业微信群机器人、飞书群机器人、Server酱（微信推送）。
仅依赖标准库。
"""

import json
import os
import urllib.request
import urllib.parse


def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        return resp.read().decode("utf-8", "ignore")
    except Exception as e:
        print("  [notify] fail:", e)
        return None


def post_form(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        return resp.read().decode("utf-8", "ignore")
    except Exception as e:
        print("  [notify] fail:", e)
        return None


def main():
    try:
        with open("data/brief.md", "r", encoding="utf-8") as f:
            brief = f.read()
    except Exception as e:
        print("no brief.md:", e)
        brief = "每日监控简报生成失败"

    sent = []

    # 企业微信群机器人
    wx = os.environ.get("WECHAT_WEBHOOK")
    if wx:
        r = post_json(wx, {"msgtype": "markdown", "markdown": {"content": brief}})
        sent.append("企业微信:%s" % (r or ""))

    # 飞书群机器人
    fs = os.environ.get("FEISHU_WEBHOOK")
    if fs:
        r = post_json(fs, {"msg_type": "text", "content": {"text": brief}})
        sent.append("飞书:%s" % (r or ""))

    # Server酱（微信推送）
    sc = os.environ.get("SERVERCHAN_KEY")
    if sc:
        title = brief.splitlines()[0].lstrip("# ").strip() if brief else "每日监控"
        r = post_form("https://sctapi.ftqq.com/%s.send" % sc,
                      {"title": title, "desp": brief})
        sent.append("Server酱:%s" % (r or ""))

    # 自定义通用 webhook（钉钉/其他，POST JSON {"text": ...} 兼容钉钉关键字场景，可选）
    generic = os.environ.get("GENERIC_WEBHOOK")
    if generic:
        post_json(generic, {"msgtype": "text", "text": {"content": brief}})
        sent.append("通用webhook")

    print("notified channels:", sent if sent else "无（未配置任何渠道）")


if __name__ == "__main__":
    main()
