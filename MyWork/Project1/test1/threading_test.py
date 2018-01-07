
import threading
import time
import queue


# def thread_test(args):
#     time.sleep(1)
#     print("Threading 1 called ",args)

# def thread_test1(args):
#     time.sleep(2)
#     print("Threading 2 is called",args)

# #if __name__ == "__main__" :
# t1 = Thread(target=thread_test, args=("thimma",))
# t2 = Thread(target=thread_test1, args=("rayan",))

# t1.start()
# t1.setDaemon
# t2.start()

# t1.join
# print(t1.is_alive())
# t2.join

# def timerthread(name,delay, repeat):
#     print("Timer: " + name + " started.....!")
#     while repeat > 0:
#         time.sleep(delay)
#         print(name + ":"+ str(time.ctime(time.time())))
#         repeat -= 1
#     print("Timer: " + name + " Completed.....!")


# def Main():
#     t1 = Thread(target=timerthread, args=("Timer1",3,5))
#     t2 = Thread(target=timerthread, args=("Timer2",2,5))
#     t1.start()
#     t2.start()
#     t1.join()
#     t2.join()
#     print("Main completed ")


# if __name__ == "__main__":
#     Main()

# tlock = threading.Lock()
# def timerthread(name,delay, repeat):
    
#     print("Timer: " + name + " started.....!")
#     tlock.acquire()
#     print(name," is acquired by Lock")
#     while repeat > 0:
#         time.sleep(delay)
#         print(name + ":"+ str(time.ctime(time.time())))
#         repeat -= 1
#     tlock.release()
#     print(name," is Released by Lock")
#     print("Timer: " + name + " Completed.....!")


# def Main():
#     t1 = threading.Thread(target=timerthread, args=("Timer1",3,5))
#     t2 = threading.Thread(target=timerthread, args=("Timer2",2,5))
#     t1.start()
#     t2.start()
#     # t1.join()
#     # t2.join()
#     print("Main completed ")


# if __name__ == "__main__":
#     Main()


# import threading
# import time

# class AsyncWriter(threading.Thread):
#     def __init__(self, text, out):
#         threading.Thread.__init__(self)
#         self.text = text
#         self.out = out


#     def run(self):
#         f = open(self.out, "a")
#         f.write(self.text +'\n')
#         f.close()
#         time.sleep(5)
#         print("Finished writing background Thread")
        
# def Main():

#     message = input("Enter your text message")
#     background = AsyncWriter(message,"out.txt")
#     background.start()
#     print("Background thread started")
#     print(background.is_alive())
#     print(background.name)
#     print(100+200)
#     background.join()
#     print("completed background thread execution and joined")

# if __name__ == "__main__":
#     Main()



# import threading
# import queue
# import time
# import random


# def flag():
#     time.sleep(3)
#     event.set()
#     print("Event is started")
#     time.sleep(7)
#     event.clear()
#     print("Event is cleared will call event wait")

# def starting_operation():
#     event.wait()
#     while event.is_set():
#         #print("Random number generation started")
#         x = random.randint(1,30)
#         print(x)
#         print("Event status", event.is_set())
#         time.sleep(1)
#         print("Event status", event.is_set())
#         if not event.is_set():
#             print("Event is not set calling break")
#             break
#     print("Event is cleared random generation stopped")

# event = threading.Event()

# t1 = threading.Thread(target=flag)
# t2 = threading.Thread(target=starting_operation)
# t1.start()
# t2.start()
# #print("Event operation is completed")


# def sleeper(n,name):
#     print(f'Hi i am {name} sleeping for {n} secondes')
#     time.sleep(n)
#     print(f'Hi i am {name} exiting...')


# # t1 = threading.Thread(target=sleeper, name="Thread1", args=(5,'Thread1'))
# # t1.start()
# # t1.join()
# # for i in ['hello','Hello','hEllO']:
# #     print(i)
# thread_list = []
# start = time.time()
# for i in range(5):
#     t = threading.Thread(target=sleeper, 
#                         name='Thread{}'.format(i), 
#                         args=(5,'Thread{}'.format(i)))

#     thread_list.append(t)
#     t.start()
# print(thread_list)

# for t in thread_list:
#     t.join()
# end = time.time()
# print(f'Time taken to run thread is: {(end-start)}')


# x=0
# count=1000000
# lock = threading.Lock()
# def add_2():
#     #with lock:
#         global x
#         for i in range(count):
#             x +=2
    
# def add_3():
#     #with lock:
#         global x
#         for i in range(count):
#             x +=3
# def sub_1():
#     #with lock:
#         global x
#         for i in range(count):
#             x -=1
# def sub_4():
#     #with lock:
#         global x

#         for i in range(count):
#             x -=4

# t1 = threading.Thread(target=add_2,)
# t2 = threading.Thread(target=add_3,)
# t3 = threading.Thread(target=sub_4,)
# t4 = threading.Thread(target=sub_1,)

# t1.start()
# t2.start()
# t3.start()
# t4.start()

# t1.join()
# t2.join()
# t3.join()
# t4.join()

#print(x)


# total = 4

# def add_value():
#     global total

#     for i in range(10):
#         print("Adding item")
#         time.sleep(1)
#         total +=1   
#     print("creation 1 is done ")

# def add_value1():
#     global total

#     for i in range(10):
#         print("Adding item")
#         time.sleep(2)
#         total +=1   
#     print("creation 2 is done")

# def limit_value():
#     global total

#     # where in the function while True is set so it will run continuesly background as Deamon though if join is not set
#     while True:

#         if total > 5:
#             print("Overloaded")
#             total -=3
#             print("Subtracted 3")
#         else:
#             time.sleep(1)
#             print("Waiting.....")

# creat1 = threading.Thread(target=add_value)
# creat2 = threading.Thread(target=add_value1)
# # if daemon is set to true it will exit if the program is running background once it completes other threads
# # join() should not be used for the daemon thread as it will wait for join() to complete.
# limit = threading.Thread(target=limit_value, daemon=True) 

# print(limit.isDaemon())

# creat1.start()
# creat2.start()
# limit.start()

# creat1.join()
# creat2.join()

# print("Total value of the count after execution", total)

# class myThread(threading.Thread):

#     def run(self):
#         print(f'{self.getName()} has Started!')
#         try:
#             if self._target:
#                 self._target(*self._args,**self._kwargs)
#         finally:
#             del self._target,self._args,self._kwargs
#             print(f"{self.getName()} has Finished")


# def sleeper(n,name):
#     print(f'Hi i am {name} sleeping for {n} secondes')
#     time.sleep(n)
#     print(f'Hi i am {name} exiting...')
        
# thread_list = []
# for i in range(5):
#     t = myThread(target=sleeper, 
#                  name='Thread{}'.format(i), 
#                  args=(5,'Thread{}'.format(i)))

#     thread_list.append(t)
#     t.start()
# #print(thread_list)

# for t in thread_list:
#     t.join()



# class myThread(threading.Thread):

#     def __init__(self,number,func,args,name=None):
#         threading.Thread.__init__(self)
#         self.number = number
#         self.func = func
#         self.args = args
#         self.name = name

#     def run(self):
#         print(f"{self.name} Calling custom run method")
#         self.func(*self.args)
#         print(f"{self.name} Exiting custom run method")

# def double(number, cycle):
#     for i in range(cycle):
#         number += number
#         #print(number)
#     print(number)

# thread_list = []
# for i in range(50):
#     t = myThread(number = i + 1,
#                 func=double,
#                 args=(i, 3),
#                 name='Thread{}'.format(i))

#     thread_list.append(t)
#     t.start()
# #print(thread_list)

# for t in thread_list:
#     t.join()

# class myThread(threading.Thread):

#     def __init__(self,number,style, *args,**kwargs):
#         super(myThread,self).__init__(*args,**kwargs)
#         self.number = number
#         self.style = style
    
#     def run(self, *args, **kwargs):
#         print(f"{self.name} Calling custom run method")
#         super(myThread,self).run(*args,**kwargs)
#         print(f"{self.name} Exiting custom run method")

# def sleeper(number,style):
#     print(f'{ number} going to to sleep in style {style}')
#     time.sleep(number)

# t = myThread(number=5,style="yellow",target=sleeper, args=[3,'Yellow'])

# t.start()
# t.join()

#Queue

# q = queue.Queue()

# for i in range(10):
#     q.put(i)

# while not q.empty():
#     print(q.get())

# def putting_thread(q):
#     while True:
#         print("starging thread")
#         time.sleep(5)
#         q.put(5)
#         print("put something")

# q = queue.Queue()
# t = threading.Thread(target=putting_thread,args=(q,), daemon=True)
# t.start()
# # x=q.get() -> will store the value in variable x
# q.put(5)
# print(q.get())
# print('first item gotton')
# print(q.get())
# #time.sleep(7)
# print("finished....")
# print(q.get())
# print(q.empty())

## FIFO

# q = queue.Queue()

# for i in range(10):
#     q.put(i)


# while not q.empty():
#     print(q.get(), end='')

# print('\n')

# #LIFO

# lq = queue.LifoQueue()

# for i in range(10):
#     lq.put(i)


# while not lq.empty():
#     print(lq.get(),end='')

# print('\n')

# #Priority Queue

# pq = queue.PriorityQueue() # Gets smallest value first

# pq.put((1,'Priority 1'))
# pq.put((3,'Priority 3'))
# pq.put((2,'Priority 2'))
# pq.put((4,'Priority 4'))

# for i in range(pq.qsize()):
#     print(pq.get()[1])



