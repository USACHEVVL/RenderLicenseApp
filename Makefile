.RECIPEPREFIX := >
.PHONY: server bot

server:
>uvicorn server.main:app --reload

bot:
>python -m telegram_bot.bot
