from multiprocessing import Pool

import time

def f(n):
    sum=0
    for x in range(100):
        sum += x*x
    return sum

if __name__== "__main__":

    t1 = time.time()
    p = Pool()
    result = p.map(f,range(100))
    p.close()
    p.join()

    print("Pool took", time.time() - t1)

    t2 = time.time()
    result1 =[]

    for x in range(100):
        result.append(f(x))
    print("serial processing took ", time.time() - t2)

