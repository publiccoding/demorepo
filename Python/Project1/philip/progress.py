#!/usr/bin/python

import sys 
import time 
import threading 

class TimeFeedbackThread(threading.Thread): 

	def __init__(self, component, componentValue):
		threading.Thread.__init__(self)
		self.component = component
		self.componentValue = componentValue
		self.stop = False

	def run(self): 
		print "Updating " + self.component + " " +  self.componentValue + " .... ", 
		sys.stdout.flush() 

		i = 0 

		while self.stop != True: 
			timeStamp = time.strftime("%H:%M:%S", time.gmtime(i))
			if i == 0:	
				sys.stdout.write(timeStamp) 
			else:
				sys.stdout.write('\b\b\b\b\b\b\b\b' + timeStamp) 
			sys.stdout.flush() 
			time.sleep(1.0) 
			i+=1 

		print ' done!'
		sys.stdout.flush() 

	def stopTimer(self):
		self.stop = True

timeFeedbackThread = TimeFeedbackThread("firmware", "tg3") 
timeFeedbackThread.start() 

time.sleep(5) 

timeFeedbackThread.stopTimer() 
timeFeedbackThread.join()

#stop = False 
#timeFeedbackThread = TimeFeedbackThread("driver", "be2net") 
#timeFeedbackThread.start() 

#time.sleep(5) 
#stop = True 
