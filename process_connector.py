import subprocess
import sys
import threading
import json
import time
import queue


class ProcessConnector():
    def __init__(self):
        self.process = None
        self.request_queue = queue.Queue()  # очередь запросов от бота
        self.response_queue = queue.Queue()  # очередь ответов для бота

    def bot_start(self):
        # Запускаем бота с двусторонними каналами
        self.process = subprocess.Popen(
            [sys.executable, "bot.py"],
            stdin=subprocess.PIPE,  # ← для отправки данных БОТУ
            stdout=subprocess.PIPE,  # ← для получения данных ОТ бота
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Поток для чтения запросов от бота
        threading.Thread(
            target=self._read_from_bot,
            daemon=True
        ).start()

        # Поток для отправки ответов боту
        threading.Thread(
            target=self._write_to_bot,
            daemon=True
        ).start()

        print("Бот запущен")

    def _read_from_bot(self):
        """Читаем запросы от бота"""
        for line in self.process.stdout:
            try:
                data = json.loads(line.strip())
                print(f"Получен запрос от бота: {data}")

                # Обрабатываем запрос
                if data.get("command") == "get_status":
                    response = {"status": "running", "time": time.time()}
                    self.response_queue.put(response)

                elif data.get("command") == "get_data":
                    response = {"data": [1, 2, 3, 4, 5]}
                    self.response_queue.put(response)

                elif data.get("command") == "shutdown":
                    print("Бот запросил выключение")
                    self.stop_bot()

            except json.JSONDecodeError:
                print(f"Неверный JSON от бота: {line}")

    def _write_to_bot(self):
        """Отправляем ответы боту"""
        while True:
            response = self.response_queue.get()  # ждем ответ
            if response is None:  # сигнал остановки
                break

            json_response = json.dumps(response) + "\n"
            self.process.stdin.write(json_response)
            self.process.stdin.flush()
            print(f"Отправлен ответ боту: {response}")

    def stop_bot(self):
        """Остановка бота"""
        if self.process:
            self.response_queue.put(None)  # сигнал остановки потока записи
            self.process.terminate()
            self.process.wait()
            print("Бот остановлен")







if __name__ == "__main__":
    connector = ProcessConnector()
    connector.bot_start()

    # Основная программа работает параллельно
    for i in range(10):
        print(f"Основная программа работает... {i}")
        time.sleep(1)

    connector.stop_bot()