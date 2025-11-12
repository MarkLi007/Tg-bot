# Tg-bot# TG Group Points Bot

群组积分机器人：消息 +1 分、每日签到 +10 分、支持 /me /rank /top。

## 快速开始
1. 在 BotFather 关闭隐私模式（/setprivacy → Disable），把机器人拉入群。
2. 复制 `.env.example` 为 `.env` 并填入 `TELEGRAM_TOKEN`。
3. 本地运行：
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   make run
