# RenderLicenseApp

## Running

Start the FastAPI server:

```bash
make server
```

Start the Telegram bot:

```bash
make bot
```

The same commands are listed in `test.py` for quick reference.

## Database

The application uses an SQLite database stored at `server/db/database.db` by default.
The path is resolved to an absolute location. You can override the database URL by
setting the `DATABASE_URL` environment variable.
