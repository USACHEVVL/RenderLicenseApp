.RECIPEPREFIX := >

.PHONY: server bot all

server:
>python -m uvicorn server.main:app --reload

bot:
>python -m telegram_bot.bot

all:
>start powershell -NoExit -Command "make server"
>start powershell -NoExit -Command "make bot"