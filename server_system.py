import os
import json
import subprocess
import time


def run(conn, core_name=None):
    print(f"SERVER: Запуск с ядром {core_name}")

    # Читаем настройки
    with open('program_settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)

    cores_path = settings.get("cores_path", "downloads_cores")

    if core_name:
        core_path = os.path.join(cores_path, core_name)

        if os.path.exists(core_path):
            # Здесь будет код запуска Minecraft сервера
            # Например:
            # java -Xmx1024M -Xms256M -jar {core_path} nogui

            print(f"Запускаю {core_path}")

            # Пример запуска (раскомментируйте когда будете готовы):
            # process = subprocess.Popen(
            #     ['java', '-Xmx1024M', '-Xms256M', '-jar', core_path, 'nogui'],
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            #     text=True
            # )

            # Эмуляция работы сервера
            while True:
                try:
                    time.sleep(1)
                    # Проверяем команды из канала
                    if conn.poll():
                        msg = conn.recv()
                        if msg.get("command") == "stop":
                            break
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Ошибка: {e}")

        else:
            print(f"Ядро {core_path} не найдено!")
            conn.send({"to_process": "connector", "command": "error", "data": f"Ядро {core_name} не найдено"})
    else:
        print("Не указано имя ядра для запуска!")