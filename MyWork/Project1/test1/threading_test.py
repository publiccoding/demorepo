
import threading
import time


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