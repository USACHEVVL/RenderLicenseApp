from pyngrok import ngrok

# если токен ещё не сохранён командой config add-authtoken,
# можно раскомментировать строку ниже:
ngrok.set_auth_token("32jpAoa7qlbLhVUNFtuRqQp0vK4_7R2pecQnULMDg1Cw35YdT")

tunnel = ngrok.connect(addr=8000, proto="http", bind_tls=True)
print("Публичный адрес:", tunnel.public_url)
print("Инспектор запросов: http://127.0.0.1:4040")

# держим процесс «живым», пока не прервёшь Ctrl+C
try:
    import time
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    ngrok.disconnect(tunnel.public_url)
    ngrok.kill()
