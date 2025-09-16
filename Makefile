.RECIPEPREFIX := >

.PHONY: server server-prod bot

server:
> uvicorn server.main:app --reload

server-prod:
> uvicorn server.main:app --host 0.0.0.0 --port 8000

bot:
> python -m telegram_bot.bot
