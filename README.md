# TG Group Points Bot

Track chat activity, award points for messages, and offer daily sign-ins for your Telegram groups.

## Quick start
1. Disable privacy mode in BotFather (`/setprivacy → Disable`) and add the bot to your group.
2. Copy `.env.example` to `.env` and set `TELEGRAM_TOKEN`.
3. In any group where the bot is present, send `/chatid` to retrieve the numeric chat identifier. If you
   want to restrict usage, add the value to `ALLOWED_CHAT_IDS` (comma separated) inside `.env`.
4. Run locally:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   make run
   ```
5. Or start with Docker:
   ```bash
   docker compose up -d
   ```

## Available commands
- `/start` – show help and configuration
- `/me` – view your score summary
- `/rank` – check your leaderboard position
- `/top` – display the top 10 members
- `/signin` – daily sign-in (UTC based)
- `/ping` – quick health check (responds with `PONG`)
- `/chatid` – show the current chat id
- `/config` – echo key runtime settings for diagnostics

### Example output
```
/top
🏆 <b>Leaderboard</b>
🥇 @Alice — <b>50</b> pts / 120 msgs
🥈 <a href="tg://user?id=222">Bob Builder</a> — <b>40</b> pts / 98 msgs
3. <a href="tg://user?id=333">Charlie</a> — <b>30</b> pts / 64 msgs
```

## Configuration
| Variable | Description | Default |
| -------- | ----------- | ------- |
| `TELEGRAM_TOKEN` | Telegram Bot token (required) | – |
| `DB_PATH` | SQLite database path | `points.db` |
| `MESSAGE_POINT` | Points per text message | `1` |
| `DAILY_SIGNIN_BONUS` | Points granted on `/signin` | `10` |
| `THROTTLE_SECONDS` | Cooldown window for message scoring | `5` |
| `LANG` | Interface language | `en` |
| `ALLOWED_CHAT_IDS` | Comma-separated chat IDs whitelist | – |

### Logging & deployment
- Logs are emitted as single-line JSON records that include the log level, timestamp, and
  frequently used identifiers (`chat_id`, `user_id`, `points`). Pipe the bot output into your
  preferred log processor for storage or alerts.
- A sample `systemd` unit is provided at `deploy/tg-points-bot.service`. Copy it to
  `/etc/systemd/system/tg-bot.service`, adjust the working directory and Python path, then run
  `sudo systemctl enable --now tg-bot` to keep the bot running in the background.

## Development helpers
- `make run` – start the bot
- `make fmt` – format code with ruff
- `make lint` – lint with ruff
- `make test` – run pytest suite

## Project structure
```
tg-group-points-bot/
├─ src/
│  ├─ bot/
│  │  ├─ __init__.py
│  │  ├─ app.py
│  │  ├─ handlers.py
│  │  ├─ lang.py
│  │  ├─ models.py
│  │  ├─ settings.py
│  │  ├─ storage.py
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

## BotFather command menu
```
start - show help
me - view my score
rank - check my leaderboard position
top - show the top members
signin - daily sign-in (+10 pts, once per day)
```
