#!/usr/bin/python

import subprocess
import logging
import time
import threading
import os
import signal
from spUtils import (RED, RESETCOLORS, TimeFeedbackThread)


'''
This class is used to apply patches to a system.  It creates an event that is used to control the timer thread
in the event of a signal needing to be handled.  Thus, keeping the printed console output organized.
'''
class ApplyPatches:

	'''
	Use the constructor to create a threading event that will be used to stop and restart the timer thread		
	when a signal (SIGINT, SIGQUIT) is captured.  Additionally, create the timer thread without a message, 
	since it will be set later depending on the type of patches being applied.
	self.exitStatus is used to inform the caller as to whether or not the program needs to exit, which would be
	the case if self.exitStatus is not 0.
	'''
        def __init__(self):

                self.timerController = threading.Event()
                self.timeFeedbackThread = ''
		self.pid = ''
		self.exitStatus = 0
		self.cancelled = 'no'
        #End __init__(self):


	'''
	This function is used to apply the patches. 
	'''
	def applyPatches(self, repositoryList, loggerName):

		logger = logging.getLogger(loggerName)

		if len(repositoryList) > 1:
			logger.info('Applying patches from repositories ' + ', '.join(repositoryList) + '.')
		else:
			logger.info('Applying patches from repository ' + repositoryList[0] + '.')

		logger.debug("The patch repository list was determined to be: " + str(repositoryList))

		#Update OS patches and install kernel patches.
		for repository in repositoryList:
			time.sleep(2)

			if 'kernel' in repository.lower():
                		self.timeFeedbackThread = TimeFeedbackThread(componentMessage = 'Installing the new kernel', event = self.timerController)
				self.timeFeedbackThread.start()

				command = 'zypper -n --non-interactive-include-reboot-patches in ' + repository + ':*'
			else:
                		self.timeFeedbackThread = TimeFeedbackThread(componentMessage = 'Applying the OS patches', event = self.timerController)
				self.timeFeedbackThread.start()

				command = 'zypper -n --non-interactive-include-reboot-patches up ' + repository + ':*'
			
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

			#We get the processes PID in case the process is cancelled and we need to kill the process.
			self.pid = result.pid
		
			out, err = result.communicate()

			logger.debug("The output of the patch update command (" + command + ") was: " + out.strip())

			if result.returncode == 0:
				logger.info("Successfully updated the system using patches from the repository " + repository + ".")
			else:
				self.timeFeedbackThread.stopTimer()
				self.timeFeedbackThread.join()

                                #Move the cursor to the next line once the timer is stopped.
                                print ''

				if self.cancelled == 'yes':
					logger.info("The patch update was cancelled by the user.")
					print RED + "The patch update was cancelled; exiting program execution." + RESETCOLORS
				else:
					logger.error("Problems were encountered while updating the system using patches from the repository " + repository + ".\n" + err)
					print RED + "Problems were encountered while applying the patches to the system; check the log file for errors; exiting program execution." + RESETCOLORS
				
				self.exitStatus = 1
				return

			self.timeFeedbackThread.stopTimer()
			self.timeFeedbackThread.join()

			#Move the cursor to the next line once the timer is stopped.
			print ''

		if len(repositoryList) > 1:
			logger.info('Done applying patches from repositories ' + ', '.join(repositoryList) + '.')
		else:
			logger.info('Done applying patches from repository ' + repositoryList[0] + '.')

	#End applyPatches(repositoryList, loggerName):


	#This function will attempt to kill the running processes as requested by the user.
	def endTask(self):
		
		try:
			self.cancelled = 'yes'
			pgid = os.getpgid(self.pid)
			os.killpg(pgid, signal.SIGKILL)
		except OSError:
			pass

	#End endTask(self):

	
	'''
	This function is used by subprocess so that signals are not propagated to the child process, which
	would result in the child process being cancelled without program control.
	'''
	def preexec(self):
                os.setpgrp()
	#End preexec(self):


	#This function is used to get the exit status of the patch update.
	def getExitStatus(self):
                return self.exitStatus
	#End getExitStatus(self):


	#This function is used to pause the timer thread when a signal is recieved.
	def pauseTimerThread(self):
                self.timeFeedbackThread.pauseTimer()
	#End pauseTimerThread(self):


	#This function is used to restart the timer thread once the signal has been handled.
        def resumeTimerThread(self):
                self.timeFeedbackThread.resumeTimer()
        #End resumeTimerThread(self):

#End ApplyPatches:


'''
#This section is for running the module standalone for debugging purposes.  Uncomment to use.
#Note it needs to be udpated before use, since the module was converted to a class.
if __name__ == '__main__':

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = 'applyPatches.log'

	repositoryList = [ 'kernelRPMs', 'OSRPMs']

        try:
                open(logFile, 'w').close()
        except IOError:
                print spUtils.RED + "Unable to access " + logFile + " for writing." + spUtils.RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.DEBUG)
	handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	applyPatches(repositoryList, loggerName)
'''
