# Telegram Admin Notifications

**Last Updated:** 2026-04-21

Real-time Telegram notifications for notable system events, delivered via a lightweight fire-and-forget module.

## Configuration

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `TELEGRAM_ENABLED` | `false` | Enable/disable all notifications |
| `TELEGRAM_BOT_TOKEN` | `""` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | `""` | Target chat (private group or channel) |

Add these to any `.env` file. All env files include the section by default (disabled).

## Events

| Event | Trigger | Emoji |
| ----- | ------- | ----- |
| `SYSTEM_STARTUP` | Server lifespan startup completes | Rocket |
| `UNHANDLED_EXCEPTION` | Catch-all exception handler (500 errors) | Fire |
| `USER_LOGIN` | Successful login via `/api/auth/login` | Key |

## Message Format

Notifications use Telegram HTML parse mode:

```
<b>[🚀] System Startup</b>

Backcast server started successfully.

<i>2026-04-21 14:30:00 UTC | hostname</i>

  <code>name</code>: John Doe
  <code>role</code>: admin
```

## Code Location

```
backend/app/core/notifications/
├── __init__.py       # Re-exports `notifier` singleton
├── _types.py         # NotificationEvent enum, NotificationPayload
└── _telegram.py      # TelegramNotifier class, singleton instance
```

## Integration Points

| File | Where | Method |
| ---- | ----- | ------ |
| `app/main.py` lifespan | After cache warming, before `yield` | `notifier.send()` (awaited) |
| `app/main.py` lifespan | After `yield` (shutdown) | `notifier.shutdown()` |
| `app/main.py` exception handler | `@app.exception_handler(Exception)` | `notifier.send_fire_and_forget()` |
| `app/api/routes/auth.py` login | After `authenticate(user)` | `notifier.send_fire_and_forget()` |

## Adding a New Event Type

1. Add member to `NotificationEvent` in `_types.py`
2. Add emoji to `_EVENT_EMOJI` dict in `_telegram.py`
3. Call `notifier.send_fire_and_forget(NotificationPayload(...))` from the relevant code

No other wiring needed.

## Design Decisions

- **Fire-and-forget**: Notifications never block request handling. Uses `asyncio.create_task()` internally.
- **Best-effort delivery**: Failures are logged at WARNING level but never propagated to callers. No retry logic.
- **Lazy httpx client**: Created on first send, closed at shutdown. Avoids event-loop issues during import.
- **Singleton pattern**: Module-level `notifier` instance imported everywhere as `from app.core.notifications import notifier`.
