import time
from multiprocessing import Process, Pipe


def f(conn):
    t = time.time()
    while True:
        time.sleep(3)
        conn.send([42, None, 'hello', time.time() - t])



def f2(conn):
    t = time.time()
    for i in range(10):
        time.sleep(1)
        conn.send([i, 'not', time.time() - t])


if __name__ == '__main__':
    # parent_conn1, child_conn1 = Pipe()
    parent_conn2, child_conn2 = Pipe()

    p2 = Process(target=f2, args=(child_conn2,))
    # p1 = Process(target=f2, args=(child_conn1,))
    # p1.start()
    p2.start()
    t = time.time()
    for i in range(5):
        time.sleep(2)
        print(parent_conn2.recv(), time.time() - t)


    # p1.terminate()
    p2.terminate()