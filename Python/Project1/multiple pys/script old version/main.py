#!/usr/bin/python

import signal
import time
import os
import curses
from threading import Thread
from doSomething import DoSomething
from testSignal import SignalHandler


#Clear the screen, since we want to the screen to have the look and feel for when we are in curses mode.
os.system('clear')

print "Phase 1: The program is starting."
print "Phase 2: Installing software."

original_sigint_handler = signal.getsignal(signal.SIGINT)
original_sigquit_handler = signal.getsignal(signal.SIGQUIT)

#Instantiate the DoSomething class.  We will be passing its main function to a worker thread.
message = "Doing some work"
doSomething = DoSomething(message)

'''
Setup signal handler to intercept SIGINT and SIGQUIT.
Need to pass in a reference to the class object that will be peforming 
the update.  That way we gain access to the TimerThread so that it can be 
stopped/started.
'''
s = SignalHandler(doSomething)

signal.signal(signal.SIGINT, s.signal_handler)
signal.signal(signal.SIGQUIT, s.signal_handler)

#Create and start the worker thread.
workerThread = Thread(target=doSomething.doSomeWork)
workerThread.start()

#Wait for the thread to either stop or get interrupted.
while 1:
	time.sleep(0.1)

	if not workerThread.is_alive():
		break

	response = s.getResponse()

	if response != '':
		if response == 'y':
			doSomething.endTask()

signal.signal(signal.SIGINT, original_sigint_handler)
signal.signal(signal.SIGQUIT, original_sigquit_handler)
