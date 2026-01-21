import sys
import json
import time
import random


def send_request(command, data=None):
    """Отправляем запрос в основной процесс"""
    request = {"command": command}
    if data:
        request.update(data)

    json_str = json.dumps(request)
    print(json_str, flush=True)  # важно: flush=True!
    return json_str


def read_response():
    """Читаем ответ от основного процесса"""
    line = sys.stdin.readline()
    if line:
        return json.loads(line.strip())
    return None


def main():
    print("Бот запущен и готов к работе", file=sys.stderr)

    while True:
        # Пример 1: Запрашиваем статус
        send_request("get_status")
        response = read_response()
        if response:
            print(f"Статус от сервера: {response}", file=sys.stderr)

        time.sleep(2)

        # Пример 2: Запрашиваем данные
        send_request("get_data", {"filter": "recent"})
        response = read_response()
        if response:
            print(f"Получены данные: {response}", file=sys.stderr)

        time.sleep(2)

        # Пример 3: Иногда запрашиваем выключение
        if random.random() < 0.1:  # 10% вероятность
            send_request("shutdown")
            print("Запрошено выключение", file=sys.stderr)
            break


if __name__ == "__main__":
    main()