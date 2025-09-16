# RenderLicenseApp

## Running

Start the FastAPI server:

```bash
make server
```

For a production deployment use:

```bash
make server-prod
```

Start the Telegram bot:

```bash
make bot
```

The same commands are listed in `test.py` for quick reference.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///server/db/database.db` (absolute path) | SQLAlchemy connection string for the app database. Override to point to another engine or path. |
| `PLAN_PRICE_RUB` | `49.00` | Subscription price (in roubles) used when creating YooKassa payments. |
| `PAYMENT_RETURN_URL` | `https://t.me/Ano3D_bot` | Redirect target after YooKassa confirms a payment. |
| `YOOKASSA_SHOP_ID` | — | YooKassa account identifier required to authorise API requests. |
| `YOOKASSA_SECRET_KEY` | — | YooKassa secret key paired with the shop ID for authenticated API calls. |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the FastAPI service that the Telegram bot calls. |
| `TELEGRAM_BOT_TOKEN` | — | Telegram Bot API token; required to run the bot and send notifications. |
| `BOT_TOKEN` | — | Alias recognised for the Telegram bot token. |
| `TOKEN` | — | Additional alias for the Telegram bot token (backwards compatibility). |

## Dependencies

- The YooKassa SDK is pinned to the stable release `yookassa==3.3.0` in `requirements.txt`
  to protect the integration from backwards incompatible API changes.

## Deployment

When deploying the Telegram bot, set the `API_BASE_URL` environment variable to the
public base URL of the FastAPI service so that the bot can reach the API. Locally the
bot defaults to `http://127.0.0.1:8000` when the variable is not provided.

## Database

The application uses an SQLite database stored at `server/db/database.db` by default.
The path is resolved to an absolute location. You can override the database URL by
setting the `DATABASE_URL` environment variable.
