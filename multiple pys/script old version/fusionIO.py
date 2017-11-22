#!/usr/bin/python

from spUtils import (RED, GREEN, RESETCOLORS, TimeFeedbackThread)
import subprocess
import logging
import shutil
import re
import time
import signal
import os


'''
This class is for Scale-up systems with Fusion-IO cards.  It creates an event that is used to control the timer thread
in the event of a signal needing to be handled.  Thus, keeping the printed console output organized.
'''
class UpdateFusionIO:

        '''
        Use the constructor to create a threading event that will be used to stop and restart the timer thread
        when a signal (SIGINT, SIGQUIT) is captured.
        '''
        def __init__(self):

                self.timerController = threading.Event()
                self.timeFeedbackThread = ''
                self.pid = ''
                self.cancelled = 'no'
                self.completionStatus = ''
        #End __init__(self):


	'''
	This function is for Scale-up systems with Fusion-IO cards and will 
	install current firmware if necessary and update the driver for the 
	new kernel.
	'''
	def updateFusionIO(patchResourceDict, loggerName, **kwargs):

		firmwareUpdateRequired = kwargs['firmwareUpdateRequired']

		logger = logging.getLogger(loggerName)

		if firmwareUpdateRequired == 'yes':
			logger.info("Updating the FusionIO firmware and software.")
			busList = (kwargs['busList']).split()
		else:
			logger.info("Updating the FusionIO software.")

		try:
			patchBaseDir = (re.sub('\s+', '', patchResourceDict['patchBaseDir'])).rstrip('/')
			fusionIOSubDir = re.sub('\s+', '', patchResourceDict['fusionIOSubDir'])

			fusionPatchDir = patchBaseDir + '/' + fusionIOSubDir
			fusionSourceDir = fusionPatchDir + '/src/'

			fusionIODriverSrcRPM = re.sub('\s+', '', patchResourceDict['fusionIODriverSrcRPM'])
		except KeyError as err:
			logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
			print RED + "A resource key was not present in the resource file; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
			self.completionStatus = 'Failure'
			return

		#Get the currently used kernel and processor type, which is used as part of the driver RPM name.
		command = 'uname -r'
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the currently used kernel was: " + out.strip())

		if result.returncode != 0:
			logger.error("Unable to get the system's current kernel information.\n" + err)
			print RED + "Unable to get the system's current kernel information; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
			self.completionStatus = 'Failure'
			return
		else:
			kernel = out.strip()

		command = 'uname -p'
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the system's processor type was: " + out.strip())

		if result.returncode != 0:
			logger.error("Unable to get the system's processor type.\n" + err)
			print RED + "Unable to get the system's processor type; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
			self.completionStatus = 'Failure'
			return
		else:
			processorType = out.strip()

		'''
		This strips off iomemory from RPM name, since it will not be needed in the regex match.
		Additionally, the source RPM is renamed to the driver RPM's name, which includes the current 
		kernel and processor type in its name.
		'''
		fusionIODriverRPM = (fusionIODriverSrcRPM.replace('iomemory-vsl', '-vsl-' + kernel)).replace('src', processorType)

		#Update the FusionIO firmware if it was determined that it is out of date.
		if firmwareUpdateRequired == 'yes':
			for bus in busList:
				time.sleep(2)
				
				message = "Updating ioDIMM in slot " + bus
                		self.timeFeedbackThread = TimeFeedbackThread(componentMessage = message, event = self.timerController)
				self.timeFeedbackThread.setComponentMessage("Updating ioDIMM in slot " + bus)
				self.timeFeedbackThread.start()

				command = "fio-update-iodrive -y -f -s " + bus + ' ' + fusionPatchDir + '/' + "*.fff"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

				#We get the processes PID in case the process is cancelled and we need to kill the process.
	                        self.pid = result.pid

				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to update the FusionIO firmware was: " + out.strip())

				self.timeFeedbackThread.stopTimer()
				self.timeFeedbackThread.join()

				#Move the cursor to the next line once the timer is stopped.
				print ''

				if result.returncode != 0:
					if self.cancelled == 'yes':
						logger.info("The FusionIO firmware update was cancelled by the user.")
						print RED + "The FusionIO firmware update was cancelled; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
					else:
						logger.error("Failed to upgrade the FusionIO firmware:\n" + err)
						print RED + "Failed to upgrade the FusionIO firmware; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS

					self.completionStatus = 'Failure'
					return

			#Remove the fio-util package before updating the software, since it is no longer needed for any firmware updates.
			command = "rpm -e fio-util"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to remove the fio-util package before updating the FusionIO software was: " + out.strip())

			if result.returncode != 0:
				logger.error("Failed to remove the fio-util package:\n" + err)
				print RED + "Failed to remove the fio-util package; check the log file for errors; the FusionIO software/driver will have to be updated manually." + RESETCOLORS
				self.completionStatus = 'Failure'
				return

		#Build the driver for the new kernel.
                self.timeFeedbackThread = TimeFeedbackThread(componentMessage = 'Updating the FusionIO driver and software', event = self.timerController)
		self.timeFeedbackThread.start()

		command = "rpmbuild --rebuild " + fusionSourceDir + "*.rpm"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

		#We get the processes PID in case the process is cancelled and we need to kill the process.
		self.pid = result.pid

		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to build the FusionIO driver was: " + out.strip())

		if result.returncode != 0:
			self.timeFeedbackThread.stopTimer()
			self.timeFeedbackThread.join()

			if self.cancelled == 'yes':
				logger.info("The FusionIO driver and software update was cancelled by the user.")
				print RED + "\nThe FusionIO driver and software update was cancelled; the FusionIO software/driver will have to be updated manually." + RESETCOLORS
			else:
				logger.error("Failed to build the FusionIO driver:\n" + err)
				print RED + "Failed to build the FusionIO driver; check the log file for errors; the FusionIO software/driver will have to be updated manually." + RESETCOLORS

			self.completionStatus = 'Failure'
			return

		out = out.strip()

		#Compile the regex that will be used to get the driver RPM location.
		fusionIODriverPattern = re.compile('.*Wrote:\s+((/[0-9,a-z,A-Z,_]+)+' + fusionIODriverRPM +')', re.DOTALL)

		logger.debug("The regex used to get the FusionIO driver RPM location was: " + fusionIODriverPattern.pattern)

		driverRPM = re.match(fusionIODriverPattern, out).group(1)

		logger.debug("The FuionIO driver was determined to be: " + driverRPM)

		#Now copy the new driver RPM to the FusionIO patch directory so that it gets installed with the rest of the RPMs.
		try:
			shutil.copy2(driverRPM, fusionPatchDir)
		except IOError as err:
			self.timeFeedbackThread.stopTimer()
			self.timeFeedbackThread.join()

			#Move the cursor to the next line once the timer is stopped.
			print ''

			logger.error("Unable to retrieve the driver RPM.\n" + err)
			print RED + "Unable to retrieve the driver RPM; check log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
			self.completionStatus = 'Failure'
			return

		#Install the FusionIO software and driver.
		command = "rpm -ivh " + fusionPatchDir + '/' + "*.rpm"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)

		#We get the processes PID in case the process is cancelled and we need to kill the process.
		self.pid = result.pid

		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to install the FusionIO software and driver was: " + out.strip())

		if result.returncode != 0:
			self.timeFeedbackThread.stopTimer()
			self.timeFeedbackThread.join()

			#Move the cursor to the next line once the timer is stopped.
			print ''

			if self.cancelled == 'yes':
				logger.info("The FusionIO driver and software installation was cancelled by the user.")
				print RED + "The FusionIO driver and software installation was cancelled; the FusionIO software/driver will have to be installed manually from " + fusionPatchDir + "." + RESETCOLORS
			else:
				logger.error("Failed to install the FusionIO software and driver:\n" + err)
				print RED + "Failed to install the FusionIO software and driver; check the log file for errors; the FusionIO software/driver will have to be installed manually from " + fusionPatchDir + "." + RESETCOLORS

			self.completionStatus = 'Failure'
			return

		if firmwareUpdateRequired == 'yes':
			logger.info("Done Updating the FusionIO firmware and software.")
		else:
			logger.info("Done Updating the FusionIO software.")

		self.timeFeedbackThread.stopTimer()
		self.timeFeedbackThread.join()

		#Move the cursor to the next line once the timer is stopped.
		print ''

		self.completionStatus = 'Success'

	#End updateFusionIO(patchResourceDict, **kwargs, loggerName):


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


        #This function is used to get the completion status (Failure or Success) of the FusionIO update.
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


#End UpdateFusionIO:


'''
#This section is for running the module standalone for debugging purposes. Uncomment to use.
if __name__ == '__main__':

	applicationResourceFile = '/hp/support/patches/resourceFiles/patchResourceFile'

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

	patchResourceDict = {}

        #Save the options for later use.
        patchResourceDict['options'] = options

        #Get patch resource file data and save it to a dictionary (hash).
        try:
                with open(applicationResourceFile) as f:
                        for line in f:
                                line = line.strip()
                                #Remove quotes from resources.
                                line = re.sub('[\'"]', '', line)

                                #Ignore commented and blank lines.
                                if len(line) == 0 or re.match("^#", line):
                                        continue
                                else:
                                        (key, val) = line.split('=')
                                        key = re.sub('\s+', '', key)
                                        patchResourceDict[key] = val.lstrip()
        except IOError as err:
                print RED + "Unable to access the application's resource file " + applicationResourceFile + ".\n" + str(err) + "\n" + RESETCOLORS
                exit(1)

	#Use the following when testing the firmware update as well.  Note, busList is a space seperated list of the fusionIO cards needing a firmware update.
	#	if updateFusionIO((patchResourceDict, firmwareUpdateRequired = 'yes', busList = '', loggerName) == 'Success':
	if updateFusionIO((patchResourceDict, firmwareUpdateRequired = 'no', loggerName) == 'Success':
		print GREEN + "Successfully upgraded the FusionIO." + RESETCOLORS
	else:
		print RED + "Failed to upgrade the FusionIO; check the log file for errors." + RESETCOLORS
'''
