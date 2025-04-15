from time import sleep
from SERV_work import ServerManager

server = ServerManager(
    jar_file="forge-1.12.2-14.23.5.2859.jar",
    cwd="Server"
)

# Запускаем сервер
server.start()

# Ждём загрузки
sleep(15)

# Отправляем команду в Minecraft чат
server.send_command("say Привет! Сервер работает!")

# Ещё немного ждём
sleep(10)

# Останавливаем сервер
server.stop()
