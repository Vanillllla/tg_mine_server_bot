import time

def main():
    try:
        while True:
            print('Скрипт работает...')
            # Здесь можно добавить основную логику скрипта
            time.sleep(5)  # Задержка в 5 секунд
    except KeyboardInterrupt:
        print('Скрипт остановлен пользователем')

if __name__ == '__main__':
    main()
