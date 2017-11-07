
import threading
import time
def worker(x):
    """ This is test method called by thread """

    print("Called worker method")
    print(threading.currentThread().getName(), 'Starting')
    while x <100:
        x +=1
    print(x)
    time.sleep(5)
    print(threading.currentThread().getName(),'Exiting')

def defender(x):
    """ This is test method called by thread """

    print("Called defender method")
    print( threading.currentThread().getName(), 'Starting' )
    while x < 100:
        x += 1
    print( x )
    time.sleep( 5 )
    print( threading.currentThread().getName(), 'Exiting' )


threads = []

def main():

        t=threading.Thread(target=worker,args=(0,))
        t1=threading.Thread(target=defender,args=(200,))
        threads.append( t )
        threads.append(t1)
        t.start()
        t.join()
        t1.start()
        t1.join()

        print(threads)

if __name__ == '__main__':
    main()