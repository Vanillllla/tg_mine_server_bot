import time
import multiprocessing

from process_connector import ProcessConnector

if __name__ == '__main__':
    pc = ProcessConnector()
    print(pc.bot_start())

while True:
    time.sleep(1)