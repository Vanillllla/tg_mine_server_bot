import time

a = ["a", "b", "c", "d", "e"]
b = {"1": "a", "2": "b", "3": "c", "4": "d", "5": "e"}
t = time.time()
print(a[4])
print(time.time()-t)

t=time.time()
print(b["5"])
print(time.time() - t)