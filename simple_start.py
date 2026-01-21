import time
from process_connector import ProcessConnector

# Создаем и запускаем бота
pc = ProcessConnector()
pc.bot_start()

print("Ждем инициализации бота...")
time.sleep(3)  # Даем боту время на запуск

try:
    while True:
        # Пример: переключение статуса сервера каждые 10 секунд
        choice = input("\nВыберите действие:\n1. Показать статус\n2. Включить/выключить сервер\n3. Выход\n> ")

        if choice == "1":
            status = pc.get_status_server()
            print(f"Текущий статус сервера: {'Запущен' if status else 'Остановлен'}")

        elif choice == "2":
            new_status = pc.start_or_stop_server()
            print(f"Сервер теперь: {'Запущен' if new_status else 'Остановлен'}")

        elif choice == "3":
            print("Выход...")
            break

        else:
            print("Неверный выбор")

except KeyboardInterrupt:
    print("\nЗавершение по Ctrl+C...")
finally:
    pc.stop_bot()
    print("Программа завершена")