# TG Group Points Bot

群组积分机器人：消息 +1 分、每日签到 +10 分、支持 /me /rank /top。

## 快速开始
1. 在 BotFather 关闭隐私模式（`/setprivacy → Disable`），把机器人拉入群。
2. 复制 `.env.example` 为 `.env` 并填入 `TELEGRAM_TOKEN`。
3. 本地运行：
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   make run
   ```
4. 通过 Docker 运行：
   ```bash
   docker compose up -d
   ```

## 可用命令
- `/start`：介绍与帮助
- `/me`：查看我的积分与发言数
- `/rank`：查看我的排名
- `/top`：查看前十
- `/signin`：每日签到（UTC 计日）

## 配置
| 变量 | 说明 | 默认值 |
| ---- | ---- | ------ |
| `TELEGRAM_TOKEN` | Telegram Bot Token（必填） | 无 |
| `DB_PATH` | SQLite 数据库存放路径 | `points.db` |
| `MESSAGE_POINT` | 每条文本消息获得的积分 | `1` |
| `DAILY_SIGNIN_BONUS` | 每日签到奖励积分 | `10` |
| `THROTTLE_SECONDS` | 单用户积分节流窗口（秒） | `5` |

## 开发命令
- `make run`：启动机器人
- `make fmt`：格式化代码（ruff）
- `make lint`：静态检查（ruff）
- `make test`：运行测试

## 项目结构
```
tg-group-points-bot/
├─ src/
│  ├─ bot/
│  │  ├─ __init__.py
│  │  ├─ app.py
│  │  ├─ handlers.py
│  │  ├─ storage.py
│  │  ├─ models.py
│  │  ├─ settings.py
│  │  └─ utils.py
│  └─ main.py
├─ .env.example
├─ requirements.txt
├─ README.md
├─ LICENSE
├─ Dockerfile
├─ docker-compose.yml
├─ Makefile
├─ pyproject.toml
└─ .github/
   ├─ ISSUE_TEMPLATE/
   │  ├─ feature_request.md
   │  ├─ bug_report.md
   │  └─ task.md
   └─ workflows/
      └─ ci.yml
```

## BotFather 命令菜单
```
start - 介绍与帮助
me - 查看我的积分
rank - 查看我在本群的排名
top - 查看本群积分榜前十
signin - 每日签到（+10分，每天限一次）
```
