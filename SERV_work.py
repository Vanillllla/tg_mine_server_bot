import subprocess
import psutil
import threading

class ServerManager:
    def __init__(self, jar_file, cwd, xmx="12G", xms="4G"):
        self.jar_file = jar_file
        self.cwd = cwd
        self.xmx = xmx
        self.xms = xms
        self.process = None
        self.output_thread = None

    def start(self):
        if self.process is None:
            self.process = subprocess.Popen(
                ["java","-Dfile.encoding=UTF-8", f"-Xmx{self.xmx}", f"-Xms{self.xms}", "-jar", self.jar_file, "nogui"],
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding = "utf-8"
            )
            print("Server started.")

            # Запускаем чтение вывода в отдельном потоке
            self.output_thread = threading.Thread(target=self.read_output, daemon=True)
            self.output_thread.start()

        else:
            print("Server is already running.")

    def read_output(self):
        try:
            for line in self.process.stdout:
                if line:
                    print("[SERVER]", line.strip())
        except Exception as e:
            print(f"Ошибка чтения stdout: {e}")

    def stop(self):
        if self.process is not None:
            try:
                parent = psutil.Process(self.process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                psutil.wait_procs(children, timeout=5)
                parent.terminate()
                parent.wait(5)
                print("Server terminated.")
            except Exception as e:
                print(f"Error during termination: {e}")
            self.process = None
        else:
            print("Server is not running.")

    def send_command(self, command):
        if self.process is not None and self.process.stdin:
            try:
                if self.process.stdin.closed:
                    print("stdin закрыт, не могу отправить команду.")
                    return
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
                print(f"Команда отправлена: {command}")
            except Exception as e:
                print(f"Ошибка при отправке команды: {e}")
        else:
            print("Сервер не запущен или stdin недоступен.")
