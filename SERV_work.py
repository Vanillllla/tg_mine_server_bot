import subprocess
import psutil

class ServerManager:
    def __init__(self, jar_file, cwd, xmx="12G", xms="4G"):
        self.jar_file = jar_file
        self.cwd = cwd
        self.xmx = xmx
        self.xms = xms
        self.process = None

    def start(self):
        if self.process is None:
            try:
                self.process = subprocess.Popen(
                    ["java", f"-Xmx{self.xmx}", f"-Xms{self.xms}", "-jar", self.jar_file, "nogui"],
                    cwd=self.cwd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,  # используем stderr для захвата ошибок
                    text=True
                )
                print("Сервер запущен.")
            except Exception as e:
                print(f"Ошибка при запуске сервера: {e}")
        else:
            print("Сервер уже работает.")

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
                print("Сервер остановлен.")
            except Exception as e:
                print(f"Ошибка при остановке сервера: {e}")
            self.process = None
        else:
            print("Сервер не запущен.")

    def send_command(self, command):
        if self.process is not None and self.process.stdin:
            try:
                # Проверим доступность stdin
                if self.process.stdin.closed:
                    print("stdin для процесса закрыт, не могу отправить команду.")
                    return
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
                print(f"Команда отправлена: {command}")
            except Exception as e:
                print(f"Ошибка при отправке команды: {e}")
        else:
            print("Сервер не запущен или stdin недоступен.")
