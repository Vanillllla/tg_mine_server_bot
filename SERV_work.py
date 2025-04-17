import subprocess
from time import sleep
import threading

class ServerManager:
    def __init__(self, jar_file, cwd, xmx="12G", xms="4G"):
        self.jar_file = jar_file
        self.cwd = cwd
        self.xmx = xmx
        self.xms = xms
        self.process = None
        self.log_buffer = []
        self._reader_thread = None
        self._lock = threading.Lock()

    def _read_output(self):
        while self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if line:
                with self._lock:
                    self.log_buffer.append(line.strip())
                    print(line.strip())  # Для вывода в терминал

    def start(self):
        if self.process is None:
            self.process = subprocess.Popen(
                ["java","-Dfile.encoding=UTF-8", f"-Xmx{self.xmx}", f"-Xms{self.xms}", "-jar", self.jar_file, "nogui"],
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding = "utf-8",
                bufsize = 1
            )
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()
            sleep(7)
            print("✅ Сервер запущен.")
            return "✅ Сервер запущен."

        else:
            print("⚠️ Сервер уже запущен.")
            return "⚠️ Сервер уже запущен."

    def stop(self):
        a = ''
        if not self.process or self.process.poll() is not None:
            print("⚠️ Сервер не запущен.")
            a += "⚠️ Сервер не запущен."
            self.process = None
            return a

        try:
            print("💾 Сохраняем миры...")
            self.send_command("save-all")

            print("🛑 Останавливаем сервер...")
            self.send_command("stop")

            # Подождём, пока сервер завершится корректно
            self.process.wait(timeout=30)
            print("✅ Сервер завершил работу.")
            a += "✅ Сервер завершил работу."
            return a
        except subprocess.TimeoutExpired:
            print("❌ Сервер не завершился вовремя.")
            a += "❌ Сервер не завершился вовремя."
            return a
        except Exception as e:
            print(f"❌ Ошибка при завершении сервера: {e}")
            a += f"❌ Ошибка при завершении сервера: {e}"
            return a
        finally:
            self.process = None

    def send_command(self, command):
        a = ''
        if self.process is None or self.process.stdin is None:
            print("⚠️ Сервер не запущен или stdin недоступен.")
            a += "⚠️ Сервер не запущен или stdin недоступен."
            return a

        try:
            with self._lock:
                old_log_len = len(self.log_buffer)

            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            print(f"✅ Команда отправлена: {command}")
            a += (f"✅ Команда отправлена: '{command}'" + "\n")
            sleep(0.25)

            with self._lock:
                new_logs = self.log_buffer[old_log_len:]

            if new_logs:
                print("📨 Ответ сервера:")
                a += ("📨 Ответ сервера:" + "\n")
                for line in new_logs:
                    print(line)
                    a += "```" + line + "```" + "\n"
                return a
            else:
                print("🔇 Сервер не вернул новых строк.")
                a += ("🔇 Сервер не вернул новых строк." + "\n")
                return a

        except Exception as e:
            print(f"❌ Ошибка при отправке команды: {e}")
            return a + f"❌ Ошибка при отправке команды: {e}"
    # def send_command(self, command):
    #     if self.process is not None and self.process.stdin:
    #         try:
    #             if self.process.stdin.closed:
    #                 print("stdin закрыт, не могу отправить команду.")
    #                 return 1
    #             self.process.stdin.write(command + "\n")
    #             self.process.stdin.flush()
    #             print(f"Команда отправлена: {command}")
    #             return 0
    #         except Exception as e:
    #             print(f"Ошибка при отправке команды: {e}")
    #             return 1
    #     else:
    #         print("Сервер не запущен или stdin недоступен.")
    #         return 2
