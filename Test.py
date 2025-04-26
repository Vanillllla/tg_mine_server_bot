from time import time, sleep

t = time()
sleep(1)
print(round(time()-t, 7))
print(time() - t)