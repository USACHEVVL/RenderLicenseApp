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
