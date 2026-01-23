# main_ui.py или ваш основной файл
import time

from process_connector import ProcessConnector

if __name__ == '__main__':
    pc = ProcessConnector()
    print(pc.bot_start())
    while True:
        time.sleep(3)