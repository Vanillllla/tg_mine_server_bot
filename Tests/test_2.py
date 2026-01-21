import os
import threading
import subprocess
import sys

print(f"Основной процесс PID: {os.getpid()}")

# 1. СОЗДАНИЕ ПОТОКА
def thread_func():
    print(f"Поток работает в процессе PID: {os.getpid()}")
    # Тот же самый PID!

thread = threading.Thread(target=thread_func)
thread.start()

# 2. СОЗДАНИЕ ПРОЦЕССА
process = subprocess.Popen(
    [sys.executable, "-c", "import os; print(f'Дочерний процесс PID: {os.getpid()}')"]
)
process.wait()

# Результат:
# Основной процесс PID: 12345
# Поток работает в процессе PID: 12345  ← ТОТ ЖЕ PID!
# Дочерний процесс PID: 12346           ← ДРУГОЙ PID!