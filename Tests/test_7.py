import threading
import time


def f(msg):
    while True:
        time.sleep(0.1)
        print(msg)

str1 = "1"
str2 = "2"
p1 = threading.Thread(target=f, args=str1)
p2 = threading.Thread(target=f, args=str2)
p1.start()
p2.start()

p2.join()