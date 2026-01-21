import subprocess
import sys
import threading
import json
import time
import queue


class ProcessConnector:
    def __init__(self):
        self.process = None
        self.response_queue = queue.Queue()  # очередь ответов для бота
        self.status = False
        self.running = False
        print("ProcessConnector is initialized")

    def bot_start(self):
        if self.process:
            print("Бот уже запущен")
            return

        try:
            self.process = subprocess.Popen(
                [sys.executable, "bot.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self.running = True

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

            # Поток для чтения ошибок бота
            threading.Thread(
                target=self._read_bot_stderr,
                daemon=True
            ).start()

            print("Бот успешно запущен")

        except Exception as e:
            print(f"Ошибка запуска бота: {e}")
            self.running = False

    def _read_from_bot(self):
        """Читаем запросы от бота"""
        while self.running:
            try:
                line = self.process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                try:
                    data = json.loads(line.strip())
                    print(f"Получен запрос от бота: {data}")

                    # Обрабатываем запрос
                    if data.get("command") == "get_status":
                        response = {
                            "request_id": data.get("request_id"),
                            "status": self.status,
                            "timestamp": time.time()
                        }
                        self.response_queue.put(response)

                except json.JSONDecodeError as e:
                    print(f"Неверный JSON от бота: {line}, ошибка: {e}")

            except Exception as e:
                if self.running:
                    print(f"Ошибка чтения от бота: {e}")
                    time.sleep(1)

    def _write_to_bot(self):
        """Отправляем ответы боту"""
        while self.running:
            try:
                # Безблокирующее получение из очереди
                try:
                    response = self.response_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if response is None:  # сигнал остановки
                    break

                json_response = json.dumps(response) + "\n"
                self.process.stdin.write(json_response)
                self.process.stdin.flush()
                print(f"Отправлен ответ боту: {response}")

            except BrokenPipeError:
                print("Бот отключился")
                break
            except Exception as e:
                if self.running:
                    print(f"Ошибка отправки боту: {e}")
                    time.sleep(1)

    def _read_bot_stderr(self):
        """Читаем stderr бота для отладки"""
        while self.running:
            try:
                line = self.process.stderr.readline()
                if line:
                    print(f"[BOT STDERR] {line.strip()}")
            except Exception as e:
                if self.running:
                    print(f"Ошибка чтения stderr бота: {e}")
                    time.sleep(1)

    def start_or_stop_server(self):
        """Включить/выключить сервер"""
        self.status = not self.status
        print(f"Статус сервера изменен на: {'Запущен' if self.status else 'Остановлен'}")
        return self.status

    def get_status_server(self):
        """Получить статус сервера"""
        return self.status

    def stop_bot(self):
        """Остановка бота"""
        if self.process:
            print("Остановка бота...")
            self.running = False
            self.response_queue.put(None)  # сигнал остановки потока записи
            time.sleep(0.5)

            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

            print("Бот остановлен")

    def __del__(self):
        """Деструктор"""
        if self.running:
            self.stop_bot()