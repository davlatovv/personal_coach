# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

A single-user Telegram bot (`aiogram` 3) that runs a personal daily routine/coaching schedule: sends timed notifications for schedule items and reminders, tracks completion, and lets the admin edit their schedule via text commands. There is no multi-tenant support — `admin_only_middleware` in `bot/main.py` silently drops any update not from `settings.admin_id`.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

./run.sh                 # start bot locally (requires .env, fails fast if missing)
python3 -m bot.main       # equivalent direct invocation

docker compose up --build   # containerized run with ./data volume mounted
docker compose logs -f bot  # stream logs

pip install pytest && pytest tests/           # run tests (pytest is not in requirements.txt)
pytest tests/test_formatters.py -k some_test  # run a single test
```

Required `.env` vars (see `bot/config.py`): `BOT_TOKEN`, `ADMIN_ID`, `DB_PATH` (default `data/schedule.db`), `TIMEZONE` (default `Asia/Tashkent`).

## Architecture

**Text-command flow only.** The bot was refactored away from inline/reply keyboards — all interaction is through slash commands and plain-text FSM prompts (see `bot/states/`). When adding a new user-facing flow, follow this pattern rather than reintroducing keyboards.

**Entry point (`bot/main.py`)**: on startup it creates tables, upserts the admin user, seeds the default schedule (`bot/database/seed.py`), registers one router per handler module, installs the admin-only outer middleware, sets bot commands, and starts the in-process scheduler. Polling only listens for `"message"` updates (no callback queries).

**Scheduler (`bot/scheduler/`)** is a hand-rolled loop, not APScheduler despite the module name suggesting otherwise:
- `scheduler.py` runs a 1-second `asyncio` loop (`_run_scheduler_loop`) that rebuilds the day's job list at midnight and fires jobs whose `"HH:MM"` matches the current time, tracking already-fired jobs in `_jobs_fired` to avoid duplicate sends.
- `day_resolver.py` determines the "day type" for a date: an explicit override in the `day_types` table takes priority over the default weekly pattern (`bot/utils/emoji.py::DEFAULT_WEEK_PATTERN`). Day type drives which `schedule_items` rows are active for a given day.
- `jobs.py` builds and sends the actual notification messages (schedule items and reminders) and logs them to `notifications_log`.

**Database (`bot/database/`)**: raw `aiosqlite`, no ORM. `db.py::create_tables()` runs `CREATE TABLE IF NOT EXISTS` plus ad-hoc, idempotent migration statements appended directly in that function (e.g. `ALTER TABLE ... ADD COLUMN`, one-off `UPDATE`/`DELETE` for schedule data fixes). There is no separate migrations framework — new schema changes are added as additional guarded statements at the bottom of `create_tables()`. Key tables: `users`, `day_types` (date → day type override), `schedule_items` (per-day-type recurring items, `is_custom` distinguishes seeded vs. user-added), `notifications_log` (delivery/completion tracking, `source_type` is `schedule` or `reminder`), `reminders` (one-off/date-ranged reminders), `custom_events` (user-added one-off events).

**Handlers (`bot/handlers/`)**: one module per command group (`start`, `schedule`, `stats`, `daytype`, `pause`, `edit`, `add`, `reminder`, `help`, `notifications`). Multi-step flows (`add`, `edit`, `reminder`) use `aiogram` FSM states from `bot/states/` with in-memory `MemoryStorage` — state is lost on restart, by design (single user, no persistence needed).

**Formatting (`bot/utils/formatters.py`)**: notification text rendering has category-specific rules — e.g. descriptions are shown for `supplement` items but suppressed for `food`/`water` items (see `tests/test_formatters.py`). Preserve this behavior when touching notification formatting.
