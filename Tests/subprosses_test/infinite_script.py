import time
import sys
import signal
import multiprocessing
from multiprocessing.managers import BaseManager


class ScriptProcess:
    def __init__(self, data_queue, stop_event, shared_dict):
        """
        Инициализация бесконечного процесса
        """
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.shared_dict = shared_dict
        self.running = True

        # Обработка сигналов для корректного завершения
        signal.signal(signal.SIGTERM, self.handle_terminate)
        signal.signal(signal.SIGINT, self.handle_terminate)

    def handle_terminate(self, signum, frame):
        """Обработчик сигналов завершения"""
        print(f"Получен сигнал {signum}, завершаем процесс...")
        self.running = False

    def process_data(self, data):
        """Обработка полученных данных"""
        print(f"Обрабатываю данные: {data}")
        # Возвращаем результат обработки
        return f"Обработано: {data.upper()}"

    def run(self):
        """Основной цикл процесса"""
        print("Бесконечный процесс запущен")

        try:
            while self.running and not self.stop_event.is_set():
                # Проверяем, есть ли новые данные в очереди
                try:
                    if not self.data_queue.empty():
                        data = self.data_queue.get_nowait()
                        result = self.process_data(data)

                        # Записываем результат в общий словарь
                        self.shared_dict['last_result'] = result
                        self.shared_dict['processed_count'] = \
                            self.shared_dict.get('processed_count', 0) + 1

                        print(f"Результат: {result}")
                except:
                    pass  # Очередь пуста

                # Выполняем основную работу процесса
                self.shared_dict['uptime'] = time.time()
                self.shared_dict['status'] = 'running'

                time.sleep(0.1)  # Небольшая пауза

        except KeyboardInterrupt:
            print("Процесс прерван пользователем")
        finally:
            print("Бесконечный процесс завершен")
            self.shared_dict['status'] = 'stopped'


# Если скрипт запущен напрямую
if __name__ == "__main__":
    # Создаем локальные объекты для тестирования
    manager = multiprocessing.Manager()
    data_queue = manager.Queue()
    stop_event = multiprocessing.Event()
    shared_dict = manager.dict()

    process = ScriptProcess(data_queue, stop_event, shared_dict)
    process.run()