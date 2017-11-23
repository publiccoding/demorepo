#!/usr/bin/python

from spUtils import (RED, GREEN, RESETCOLORS, TimeFeedbackThread)
import subprocess
import logging
import os
import signal
import threading


'''
This class is used to build the deadman driver on a Serviceguard system.  It creates an event that is used to control the timer thread
in the event of a signal needing to be handled.  Thus, keeping the printed console output organized.
'''
class BuildDeadmanDriver:

        '''
        Use the constructor to create a threading event that will be used to stop and restart the timer thread
        when a signal (SIGINT, SIGQUIT) is captured.
        '''
        def __init__(self):

                self.timerController = threading.Event()
                self.timeFeedbackThread = TimeFeedbackThread(componentMessage = "Rebuilding and installing the deadman driver", event = self.timerController)
                self.pid = ''
                self.cancelled = 'no'
		self.completionStatus = ''
        #End __init__(self):

	'''
	This function is used to configure the deadman driver on Serviceguard systems.
	'''
	def buildDeadmanDriver(self, loggerName):
		
		sgDriverDir = '/opt/cmcluster/drivers'
		logger = logging.getLogger(loggerName)

		logger.info("Rebuilding and installing the deadman driver for the new kernel.")

		#Save the current working directory, so that we can return to it after building the driver.
		cwd = os.getcwd()

		try:
			os.chdir(sgDriverDir)
		except OSError as err:
				logger.error("Could not change into the deadman drivers directory (" + sgDriverDir + ").\n" + str(err))
				print RED + "Could not change into the deadman drivers directory; check the log file for errors; the deadman driver will have to be manually built/installed." + RESETCOLORS
				self.completionStatus = 'Failure'
				return

		driverBuildCommandsList = ['make modules', 'make modules_install', 'depmod -a']

		self.timeFeedbackThread.start()

		for command in driverBuildCommandsList:
			buildCommand = command
			result = subprocess.Popen(buildCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

			#We get the processes PID in case the process is cancelled and we need to kill the process.
                        self.pid = result.pid

			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used in building and installing the deadman driver was: " + out.strip())

			if result.returncode != 0:
				self.timeFeedbackThread.stopTimer()
				self.timeFeedbackThread.join()

                                #Move the cursor to the next line once the timer is stopped.
                                print ''

				if self.cancelled == 'yes':
                                        logger.info("The deadman driver build and install was cancelled by the user.")
                                        print RED + "The deadman driver build and install was cancelled; the deadman driver will have to be manually built/installed." + RESETCOLORS
				else:
					logger.error("Failed to build and install the deadman driver.\n" + err)
					print RED + "Failed to build and install the deadman driver; check the log file for errors; the deadman driver will have to be manually built/installed." + RESETCOLORS

				self.completionStatus = 'Failure'
				return

		self.timeFeedbackThread.stopTimer()
		self.timeFeedbackThread.join()

		#Move the cursor to the next line once the timer is stopped.
		print ''

		try:
			os.chdir(cwd)
		except:
			pass

		logger.info("Done rebuilding and installing the deadman driver for the new kernel.")

		self.completionStatus = 'Success'

	#End buildDeadmanDriver(loggerName):


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


        #This function is used to get the completion status (Failure or Success) of the deadman build/install.
        def getCompletionStatus(self):
                return self.completionStatus
        #End getExitStatus(self):


        #This function is used to pause the timer thread when a signal is recieved.
        def pauseTimerThread(self):
                self.timeFeedbackThread.pauseTimer()
        #End pauseTimerThread(self):


        #This function is used to restart the timer thread once the signal has been handled.
        def resumeTimerThread(self):
                self.timeFeedbackThread.resumeTimer()
        #End resumeTimerThread(self):

#End BuildDeadmanDriver:


'''
#This section is for running the module standalone for debugging purposes. Uncomment to use.
#Note it needs to be udpated before use, since the module was converted to a class.
if __name__ == '__main__':

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = 'postUpdate.log'

        try:
                open(logFile, 'w').close()
        except IOError:
                print RED + "Unable to access " + logFile + " for writing." + RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.DEBUG)
	handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	if buildDeadmanDriver(loggerName) == 'Success':
		print GREEN + "Successfully built and installed the deadman driver." + RESETCOLORS
	else:
		print RED + "Failed to build and install the deadman driver; check the log file for errors." + RESETCOLORS
'''
