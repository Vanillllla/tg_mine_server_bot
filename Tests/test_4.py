import time

a=[0,1,2,3,4,5,6,7,8]
b={0:0,1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8}
c ={'a':1,'b':2,'c':3,'d':4,'e':5}

t=time.time()
print(a[5], time.time() - t)
t=time.time()
print(b[5], time.time() - t)
t=time.time()
print(c['e'], time.time() - t)