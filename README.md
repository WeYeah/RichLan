# RichLan · 飞龙股份 & 英维克 股市监控看板

一个轻量的 A 股监控看板，聚焦两只液冷产业链标的：

- **飞龙股份（002536.SZ）** — 液冷泵·国产替代
- **英维克（002837.SZ）** — 液冷温控龙头

## 功能

| 模块 | 说明 |
|---|---|
| 📈 股价走势 | 实时行情（腾讯免费接口，10 秒刷新）+ 前复权日 K 线（MA5/10/20 + 成交量） |
| 🎯 投资分析 | 核心逻辑、估值、订单/基本面、买卖点框架 |
| 📊 财报变动 | 营收/归母/毛利率对照 + 归母净利润趋势 |
| 🌐 市场分析 | 板块环境、资金流向、机构评级 |
| 🧭 信心变化 | 综合信心指数（0–100，四因子合成）+ 看多/看空信号分解 |
| 🔔 价格告警 | 价格上/下限、涨跌幅阈值，触发时页面弹窗 + 提示音 |

## 部署（GitHub Pages）

1. 仓库 **Settings → Pages**，Source 选择 **Deploy from a branch → `main` / `(root)`**，保存。
2. 稍等片刻，访问 `https://<你的用户名>.github.io/RichLan/`。

## 自动更新与推送（GitHub Actions）

- `scripts/update.py` 每个交易日北京时间 15:30（收盘后）自动运行，拉取最新行情、重算信心指数，更新 `data/snapshot.json`。
- `scripts/notify.py` 把每日简报推送到配置的通知渠道。
- 通知渠道通过仓库 **Settings → Secrets and variables → Actions** 配置（可选）：

| Secret | 说明 |
|---|---|
| `WECHAT_WEBHOOK` | 企业微信群机器人 Webhook |
| `FEISHU_WEBHOOK` | 飞书群机器人 Webhook |
| `SERVERCHAN_KEY` | Server酱 SendKey（微信推送） |
| `GENERIC_WEBHOOK` | 自定义通用 Webhook |

> 至少配置一个才会推送；一个都不配则只更新数据、不推送。

## 数据说明

- 行情 / K 线：腾讯免费行情接口，无需 Key。
- 财报 / 研报：公司公告、公开研报（季度/半年度发布，非每日更新）。
- 信心指数为量化合成指标，仅供参考，不构成投资建议。

## 本地运行

直接双击 `index.html`（需联网加载行情与 `data/snapshot.json`）；或起一个静态服务器：

```bash
python -m http.server 8000
# 打开 http://localhost:8000
```

## 免责声明

本项目仅供学习研究使用，基于公开数据与量化分析，不构成任何投资建议。市场有风险，投资需谨慎。
