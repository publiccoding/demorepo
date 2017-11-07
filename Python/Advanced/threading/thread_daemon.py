import threading
import time
import logging


# logging.basicConfig(level=logging.DEBUG,
#                     format='[%(levelname)s] (%(threadName)-10s) %(message)s')


def worker_deamon():
    #logging.DEBUG(threading.currentThread().getName())
    print(threading.currentThread().getName()+'Started')
    time.sleep(5)
    print(threading.currentThread().getName()+'Existing')

def worker_non_deamon():
    #logging.DEBUG(threading.currentThread().getName())
    print(threading.currentThread().getName()+ 'Started' )
    time.sleep( 5 )
    print(threading.currentThread().getName()+'Existing' )


d = threading.Thread(target=worker_deamon)
t = threading.Thread(target=worker_non_deamon)
d.setDaemon(True)

d.start()
t.start()
d.join(1)
print("is __Alive()", d.isAlive())
t.join()