import multiprocessing
import time


def f():
    while True:
        time.sleep(1)

p = multiprocessing.Process(target=f)
# print([method for method in dir(p) if not method.startswith('_')])
# print(p.is_alive())
p.start()
time.sleep(1)
# p.terminate()
# print(p.exitcode)
# print(p.is_alive())
# print(p.sentinel)
# print(p.ident)

time.sleep(10)