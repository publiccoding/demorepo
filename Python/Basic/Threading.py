""" Module Doc string s"""
# import threading
# import time
#
# class BackgroundThread(threading.Thread):
#     """ Class Docstring """
#
#     def __init__(self, text, out):
#         """ Thread constructor """
#         threading.Thread.__init__(self)
#         self.text = text
#         self.out = out
#     def run(self):
#         """Thread call method"""
#         f = open(self.out, "a")
#         f.write(self.text +'\n')
#         f.close()
#         time.sleep(3)
#         print("Finished Background program write is completed" + self.out)
#
#
# def main():
#     msg = input("Enter you message")
#     background = BackgroundThread(msg,'out.txt')
#     background.start()
#     print("Program can continue to run while it is in background")
#     print( 100 + 400)
#     background.join()
#     print("Thread joined and compelted ")
#
#
# if __name__ == '__main__':
#     main()
#

#from threading import Thread
# import time
#
#
# def timer(name , delay, repeat):
#     print("Timer"+ name + "Started ")
#
#     while repeat > 0 :
#         time.sleep(delay)
#         print(name +":"+ str(time.ctime(time.time())))
#         repeat -=1
#     print("Timer "+ name + "completed")
#
# def main():
#
#     t1 = Thread(target=timer, args=("Timer1", 1, 5))
#     t2 = Thread(target=timer, args=("Timer2", 2, 5))
#     t1.start()
#     t2.start()
#     print("Main Program completed ")
#
# if __name__ == '__main__':
#     main()
#
#
#
# #!/usr/bin/python
#
# import sys
# import time
# import threading
#
# class TimeFeedbackThread(threading.Thread):
#
#     def __init__(self, component, componentValue):
#         threading.Thread.__init__(self)
#         self.component = component
#         self.componentValue = componentValue
#         self.stop = False
#
#
#     def run(self):
#         print("Updating " + self.component + " " +  self.componentValue + " .... ")
#        # sys.stdout.flush()
#
#         i = 0
#
#         while self.stop != True:
#
#             timeStamp = time.strftime("%H:%M:%S", time.gmtime(i))
#            # print("value of i before if "+str(i))
#             if i == 0:
#                 sys.stdout.write(timeStamp)
#             else:
#               #  print("value of i inside else"+ str(i))
#                 sys.stdout.write('\b\b\b\b\b\b\b\b' + timeStamp)
#             sys.stdout.flush()
#             time.sleep(1.0)
#             i+=1
#
#         #print("value of i inside outside while" + str(i))
#         print(' done!')
#        # sys.stdout.flush()
#
#
#     def stopTimer(self):
#         print("calling stopTimver")
#         self.stop = True
#
# timeFeedbackThread = TimeFeedbackThread("firmware", "tg3")
# timeFeedbackThread.start()
#
# time.sleep(5)
#
# timeFeedbackThread.stopTimer()
# timeFeedbackThread.join()
#
# #stop = False
# #timeFeedbackThread = TimeFeedbackThread("driver", "be2net")
# #timeFeedbackThread.start()
#
# #time.sleep(5)
# #stop = True