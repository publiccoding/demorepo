#!/usr/bin/python

import re
import signal
import time
import sys
import os
import optparse
import traceback
import datetime
from threading import Thread
from modules.computeNodeInventory import (ComputeNodeInventory, Gen1ScaleUpComputeNodeInventory)
from modules.csurUpdateUtils import (RED, RESETCOLORS, SignalHandler)
from modules.csurUpdateInitialize import Initialize
from modules.computeNodeUpdate import ComputeNodeUpdate
from modules.updateReleaseInformation import updateVersionInformationFile
from modules.cursesThread import CursesThread



'''
This is the main function from which the program is ran.
'''
def main():
	if os.geteuid() != 0:
		print(RED + "You must be root to run this program; exiting program execution." + RESETCOLORS)
		exit(1)

	programVersion = '1.2-rc1'

	#Parse options before setting up curses mode.
	usage = 'usage: %prog [[-h] [-r] [-u] [-v]]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-r', action='store_true', default=False, help='This option is used to generate a version report.')
	parser.add_option('-u', action='store_true', default=False, help='This option is used to update the local OS hard drives before the mirror is split.')
	parser.add_option('-v', action='store_true', default=False, help='This option is used to display the application\'s version.')

	(options, args) = parser.parse_args()

	if options.v:
		print(os.path.basename(sys.argv[0]) + ' ' + programVersion)
		exit(0)

	count = 0

	for option in options:
		if options[option]:
			count += 1

	if count > 1:
		print(RED + "Options are mutually exclusive; please try again; exiting program execution." + RESETCOLORS)
		exit(1)

	if options.r:
		versionInformationLogOnly = True
	else:
		versionInformationLogOnly = False

	if options.u:
		updateOSHarddrives = True
	else:
		updateOSHarddrives = False

	#This is the location of the csur application.
	csurBasePath = '/hp/support/csur'

	'''
	These log files have their name hardcoded, since their logging starts before the
	csur application's resource file is read.
	'''	
	currentLogDir = datetime.datetime.now().strftime("Date_%d%b%Y_Time_%H:%M:%S")
	logBaseDir = csurBasePath + '/log/' + currentLogDir + '/'
	sessionScreenLog = logBaseDir + 'sessionScreenLog.log'
	cursesLog = logBaseDir + 'cursesLog.log'

        try:
                os.mkdir(logBaseDir)
	except OSError as err:
		print(RED + 'Unable to create the current log directory ' + logBaseDir + '; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
		exit(1)

	try:
		'''
		The application uses curses to manage the display so that we have two 
		windows. One for feedback and one for conversing.  Also, scrolling is implemented.
		'''
		cursesThread = CursesThread(sessionScreenLog, cursesLog)
		cursesThread.daemon = True
		cursesThread.start()

		initialize = Initialize(cursesThread)

		csurResourceDict = initialize.init(csurBasePath, logBaseDir, programVersion, versionInformationLogOnly, updateOSHarddrives)

		if options.r:
			cursesThread.insertMessage(['informative', 'The system version report has been created and is in the log directory.'])
			cursesThread.insertMessage(['info', ' '])
		else:
			#The computeNodeList will be empty if the node did not need to be updated.
			if len(csurResourceDict['componentListDict']['computeNodeList']) == 0:
				cursesThread.insertMessage(['informative', 'The compute node is already up to date; no action taken.'])
			else:
				'''
				For a Scale-up system/Compute Nodes only there will only be two timer threads.  One for the initial initialization 
				and a second for the update.			
				'''
				timerThreadLocation = 1

				computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
				hostname = computeNodeDict['hostname']

				if updateOSHarddrives:
					cursesThread.insertMessage(['informative', "Phase 2: Updating compute node " + hostname + "'s hard drives that need to be updated."])
				else:
					cursesThread.insertMessage(['informative', "Phase 2: Updating the compute node " + hostname + "'s components that need to be updated."])
					
				#Instantiate the computeNode update class, which will do the work of updating the compute node.
				computeNodeUpdate = ComputeNodeUpdate(cursesThread, csurResourceDict.copy(), timerThreadLocation)

				#Get the current signal handlers so that they can be restored after the update is completed.
				original_sigint_handler = signal.getsignal(signal.SIGINT)
				original_sigquit_handler = signal.getsignal(signal.SIGQUIT)

				'''
				Setup signal handler to intercept SIGINT and SIGQUIT.
				'''

				s = SignalHandler(cursesThread)

				signal.signal(signal.SIGINT, s.signal_handler)
				signal.signal(signal.SIGQUIT, s.signal_handler)

				#Create and start the worker thread.
				workerThread = Thread(target=computeNodeUpdate.updateComputeNodeComponents)
				workerThread.start()

				#Wait for the thread to either stop or get interrupted.
				while 1:
					time.sleep(0.1)

					if not workerThread.is_alive():
						break

					'''
					The response will be an empty string unless a signal was received.  If a signal is
					received then response is either 'n' (Don't cancel the update) or 'y' (Cancel the update.).
					'''
					response = s.getResponse()

					if response != '':
						if response == 'y':
							computeNodeUpdate.endTask()
							cursesThread.join()
							exit(1)

				#Restore the original signal handlers.
				signal.signal(signal.SIGINT, original_sigint_handler)
				signal.signal(signal.SIGQUIT, original_sigquit_handler)

				componentProblemDict = computeNodeUpdate.getUpdateComponentProblemDict()

				#Update the CSUR version information file.
				if not updateOSHarddrives:
					updateVersionInformationFileResult = updateVersionInformationFile(csurResourceDict.copy())

				#Move cursor down for formatting purposes.
				cursesThread.insertMessage(['info', ' '])

				if len(componentProblemDict['Software']) == 0 and len(componentProblemDict['Drivers']) == 0 and len(componentProblemDict['Firmware']) == 0:	
					if not updateOSHarddrives:
						if not updateVersionInformationFileResult:
							cursesThread.insertMessage(['warning', 'The update of compute node ' + hostname + ' completed succesfully, however, the version information file update failed; check the log file for errors and update the file manually.'])
							cursesThread.insertMessage(['info', ' '])
							if computeNodeDict['externalStoragePresent']:
								cursesThread.insertMessage(['final', 'Once the version information file is updated, power cycle the attached storage controller(s) and reboot the system for the changes to take effect.'])
							else:
								cursesThread.insertMessage(['final', 'Once the version information file is updated, reboot the system for the changes to take effect.'])
						else:
							cursesThread.insertMessage(['informative', 'The update of compute node ' + hostname + ' completed succesfully.'])
							cursesThread.insertMessage(['info', ' '])
							if computeNodeDict['externalStoragePresent']:
								cursesThread.insertMessage(['final', 'Power cycle the attached storage controller(s) and reboot the system for the changes to take effect.'])
							else:
								cursesThread.insertMessage(['final', 'Reboot the system for the changes to take effect.'])
					else:
						cursesThread.insertMessage(['informative', 'The update of compute node ' + hostname + ' completed succesfully.'])
						cursesThread.insertMessage(['info', ' '])
						cursesThread.insertMessage(['final', 'Reboot the system for the changes to take effect.'])
				else:
					if not updateOSHarddrives:
						errorMessage = 'The following components encountered errors during the update of compute node ' + hostname + '; check the log file for errors:\n'
						
						if len(componentProblemDict['Software']) != 0:
							'''
							Print the keys which are the names of the software package(s) that had issues while being installed. Else
							print the names of the software package(s) that had issues while being removed/installed.
							'''
							if not 'rpmRemovalFailure' in componentProblemDict['Software']:
								errorMessage += 'Software: ' + ', '.join(componentProblemDict['Software'].keys()) + '\n'
							else:
								if len(componentProblemDict['Software']) == 1:
									errorMessage += 'Software: ' + componentProblemDict['Software']['rpmRemovalFailure'] + '\n'
								else:
									errorMessage += 'Software: ' + componentProblemDict['Software']['rpmRemovalFailure'] + ', '
									del componentProblemDict['Software']['rpmRemovalFailure']
									errorMessage += ', '.join(componentProblemDict['Software'].keys()) + '\n'

						if len(componentProblemDict['Drivers']) != 0:
							errorMessage += 'Drivers: '  + ', '.join(componentProblemDict['Drivers'].keys()) + '\n'

						if len(componentProblemDict['Firmware']) != 0:
							errorMessage += 'Firmware: ' + ', '.join(componentProblemDict['Firmware'].keys()) + '\n'

						if not updateVersionInformationFileResult:
							errorMessage += 'Also, the version information file update failed; check the log file for errors and update the file manually.'

						cursesThread.insertMessage(['error', errorMessage])
					else:
						cursesThread.insertMessage(['error', "Errors were encountered while updating compute node " + hostname + "'s hard drive firmware; check the log file for errors."])

		cursesThread.insertMessage(['info', ' '])

		cursesThread.getUserInput(['informative', 'Press enter to exit.'])

		while not cursesThread.isUserInputReady():
			time.sleep(0.1)

	except Exception:
		cursesThread.join()
		traceback.print_exc()
		exit(1)
	finally:
		cursesThread.join()
#End main():

main()
