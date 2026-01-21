import multiprocessing
import time
import sys
import os
from infinite_script import ScriptProcess
import shared_module


class MainController:
    def __init__(self):
        """Инициализация главной программы"""
        self.child_process = None
        self.data_queue = None
        self.stop_event = None
        self.shared_dict = None

    def start_child_process(self):
        """Запуск дочернего процесса"""
        print("Запуск дочернего процесса...")

        # Инициализируем общие данные
        self.data_queue, self.stop_event, self.shared_dict = \
            shared_module.init_shared_data()

        # Создаем и запускаем процесс
        self.child_process = multiprocessing.Process(
            target=self.run_child_script,
            args=(self.data_queue, self.stop_event, self.shared_dict)
        )
        self.child_process.daemon = True  # Процесс завершится с главным
        self.child_process.start()

        print(f"Дочерний процесс запущен с PID: {self.child_process.pid}")
        return True

    def run_child_script(self, data_queue, stop_event, shared_dict):
        """Функция, которая запускается в дочернем процессе"""
        process = ScriptProcess(data_queue, stop_event, shared_dict)
        process.run()

    def send_data_to_child(self, data):
        """Отправка данных дочернему процессу"""
        if self.data_queue:
            self.data_queue.put(data)
            print(f"Данные отправлены: {data}")
            return True
        else:
            print("Ошибка: процесс не запущен")
            return False

    def get_data_from_child(self):
        """Получение данных от дочернего процесса"""
        if self.shared_dict:
            return dict(self.shared_dict)  # Копируем словарь
        return {}

    def stop_child_process(self):
        """Остановка дочернего процесса"""
        if self.child_process and self.child_process.is_alive():
            print("Остановка дочернего процесса...")
            self.stop_event.set()  # Устанавливаем флаг остановки

            # Даем процессу время на корректное завершение
            self.child_process.join(timeout=5)

            if self.child_process.is_alive():
                print("Принудительное завершение...")
                self.child_process.terminate()
                self.child_process.join()

            print("Дочерний процесс остановлен")
            return True
        else:
            print("Процесс уже остановлен")
            return False

    def check_child_status(self):
        """Проверка статуса дочернего процесса"""
        if self.child_process:
            return {
                'alive': self.child_process.is_alive(),
                'pid': self.child_process.pid,
                'exitcode': self.child_process.exitcode
            }
        return {'alive': False}

    def run_interactive(self):
        """Интерактивный режим работы"""
        print("=== Управление дочерним процессом ===")
        print("1. Запустить процесс")
        print("2. Отправить данные")
        print("3. Получить данные")
        print("4. Проверить статус")
        print("5. Остановить процесс")
        print("6. Выход")

        while True:
            try:
                choice = input("\nВыберите действие (1-6): ").strip()

                if choice == '1':
                    if self.start_child_process():
                        print("Процесс успешно запущен")

                elif choice == '2':
                    data = input("Введите данные для отправки: ").strip()
                    self.send_data_to_child(data)

                elif choice == '3':
                    data = self.get_data_from_child()
                    print(f"Данные от дочернего процесса: {data}")

                elif choice == '4':
                    status = self.check_child_status()
                    print(f"Статус: {status}")

                elif choice == '5':
                    self.stop_child_process()

                elif choice == '6':
                    print("Завершение работы...")
                    self.stop_child_process()
                    break

                else:
                    print("Неверный выбор")

            except KeyboardInterrupt:
                print("\nЗавершение по Ctrl+C...")
                self.stop_child_process()
                break
            except Exception as e:
                print(f"Ошибка: {e}")


# Альтернативный вариант: использование subprocess
class SubprocessController:
    """Контроллер с использованием subprocess для запуска скрипта"""

    def __init__(self):
        self.process = None

    def start_with_subprocess(self):
        """Запуск скрипта через subprocess"""
        import subprocess
        import json

        print("Запуск через subprocess...")

        # Запускаем скрипт как отдельный процесс
        self.process = subprocess.Popen(
            [sys.executable, 'infinite_script.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        print(f"Процесс запущен с PID: {self.process.pid}")
        return True

    def send_to_subprocess(self, data):
        """Отправка данных в subprocess через stdin"""
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(data + '\n')
                self.process.stdin.flush()
                print(f"Данные отправлены: {data}")
                return True
            except Exception as e:
                print(f"Ошибка отправки: {e}")
                return False
        return False

    def stop_subprocess(self):
        """Остановка subprocess"""
        if self.process:
            print("Остановка subprocess...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("Subprocess остановлен")
            return True
        return False


if __name__ == "__main__":
    # Запуск в интерактивном режиме
    controller = MainController()
    controller.run_interactive()