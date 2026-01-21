import multiprocessing
import queue


# Создаем общие переменные для обмена данными между процессами
def init_shared_data():
    # Очередь для передачи данных от главного процесса к дочернему
    manager = multiprocessing.Manager()
    data_queue = manager.Queue()  # Потокобезопасная очередь

    # Событие для остановки дочернего процесса
    stop_event = multiprocessing.Event()

    # Общий словарь для данных (если нужно)
    shared_dict = manager.dict()

    return data_queue, stop_event, shared_dict