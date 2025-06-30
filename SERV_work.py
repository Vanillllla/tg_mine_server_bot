import subprocess
import threading
import time
import os
from datetime import datetime

class ServerManager:
    def __init__(self, jar_file, cwd, xmx="8G", xms="4G", log_dir="logs"):
        self.jar_file = jar_file
        self.cwd = cwd
        self.xmx = xmx
        self.xms = xms
        self.process = None
        self.ssh_p = None
        self._output_buffer = []
        self._lock = threading.Lock()
        self._reader_thread = None

        # Папка и файл логов
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file_path = os.path.join(self.log_dir, "server.log")

    def _log(self, message):
        """Вывод сообщения в консоль и запись в файл."""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        full_message = f"{timestamp} {message}"
        print(full_message)
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(full_message + "\n")

    def _read_output(self):
        """Фоновый поток чтения stdout сервера."""
        while self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if line:
                line = line.strip()
                self._log(f"[SERVER] {line}")
                with self._lock:
                    self._output_buffer.append(line)

    def start(self):
        """Запуск сервера."""
        if self.process is not None and self.process.poll() is None:
            self._log("⚠️ Сервер уже запущен.")
            return "⚠️ Сервер уже запущен."

        command = [
            "ssh",
            "-N",  # Не выполнять удалённые команды
            "-R", "25564:localhost:25565",  # Проброс порта
            "root@xazux.ru",
            "-i", "../id_ed25519_xazuxru",  # SSH-ключ
            "-o", "ServerAliveInterval=60"  # Keepalive
        ]

        self.ssh_p = subprocess.Popen(
            command,  # Передаём готовую команду
            cwd=self.cwd,  # Рабочая директория
            encoding="utf-8",  # Кодировка
            bufsize=1,  # Буферизация строк
            # Дополнительно можно перенаправить потоки при необходимости:
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL  # Игнорируем ввод
        )
        self.process = subprocess.Popen(
            ["java", "-Dfile.encoding=UTF-8", f"-Xmx{self.xmx}", f"-Xms{self.xms}", "-jar", self.jar_file, "nogui"],
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1
        )

        self._output_buffer.clear()

        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()

        self._log("⏳ Ожидание запуска сервера...")
        start_time = time.time()
        while True:
            with self._lock:
                if any("Done (" in line and ")! For help, type" in line for line in self._output_buffer):
                    self._log("✅ Сервер полностью запущен.\n⏳Полное время запуска сервера: " + str(round(time.time()-start_time, 2)) + " сек.")
                    return ("✅ Сервер полностью запущен.\n⏳Полное время запуска сервера: " + str(round(time.time()-start_time, 2)) + " сек.")

            if self.process.poll() is not None:
                self._log("❌ Сервер процесс неожиданно завершился.")
                return "❌ Сервер процесс неожиданно завершился."

            if time.time() - start_time > 180:
                self._log("❌ Таймаут ожидания запуска сервера (180 секунд).")
                return "❌ Таймаут ожидания запуска сервера."

            time.sleep(1)

    def send_command(self, command):
        """Отправка команды серверу и вывод ответа."""
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            self._log("⚠️ Сервер не запущен или stdin недоступен.")
            return "⚠️ Сервер не запущен или stdin недоступен."

        try:
            with self._lock:
                old_log_len = len(self._output_buffer)

            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            self._log(f"✅ Команда отправлена: '{command}'")

            time.sleep(1.5)  # Дать серверу время на ответ

            with self._lock:
                new_logs = self._output_buffer[old_log_len:]

            if new_logs:
                self._log("📨 Ответ сервера:")
                for line in new_logs:
                    self._log(line)
                return "\n".join(new_logs)
            else:
                self._log("🔇 Сервер не вернул новых строк.")
                return "🔇 Сервер не вернул новых строк."

        except Exception as e:
            self._log(f"❌ Ошибка при отправке команды: {e}")
            return f"❌ Ошибка при отправке команды: {e}"

    def stop(self):
        """Корректная остановка сервера."""
        if not self.process or self.process.poll() is not None:
            self._log("⚠️ Сервер не запущен.")
            self.process = None
            return "⚠️ Сервер не запущен."


        try:
            self.ssh_p.terminate()

            self._log("💾 Сохраняем миры...")
            self.send_command("save-all")

            self._log("🛑 Останавливаем сервер...")
            self.send_command("stop")

            self.process.wait(timeout=30)
            self._log("✅ Сервер корректно остановлен.")

            return "✅ Сервер корректно остановлен."

        except subprocess.TimeoutExpired:
            self._log("❌ Сервер не остановился вовремя!")
            self.process.kill()
            return "❌ Сервер не остановился вовремя!"
        except Exception as e:
            self._log(f"❌ Ошибка при остановке сервера: {e}")
            self.process.terminate()
            return f"❌ Ошибка при остановке сервера: {e}"
        finally:
            self.process = None
            self.ssh_p = None
