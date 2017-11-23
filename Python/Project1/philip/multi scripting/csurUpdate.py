#!/usr/bin/python

import re
import signal
import time
import sys
import os
import optparse
import traceback
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

	programVersion = '1.0-0'
	#Parse options before setting up curses mode.
	usage = 'usage: %prog [[-d] [-h] [-v]]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-d', action='store_true', default=False, help='This option is used when problems are encountered and additional debug information is needed.')
	parser.add_option('-v', action='store_true', default=False, help='This option is used to display the application\'s version.')

	(options, args) = parser.parse_args()

	if options.v:
		print(os.path.basename(sys.argv[0]) + ' ' + programVersion)
		exit(0)

	if options.d:
		debug = True
	else:
		debug = False

	#This is the location of the application.
	csurBasePath = '/hp/support/csur'

	'''
	These log files have their name hardcoded, since their logging starts before the
	application's resource file is read.
	'''	
	logBaseDir = csurBasePath + '/log/'
	sessionScreenLog = logBaseDir + 'sessionScreenLog.log'
	cursesLog = logBaseDir + 'cursesLog.log'

	#Always start with an empty log directory when performing a new update.
	try:
		logList = os.listdir(logBaseDir)

		for log in logList:
			os.remove(logBaseDir + log)
	except OSError as err:
		print(RED + 'Unable to remove old logs in ' + logBaseDir + '; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
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

		csurResourceDict = initialize.init(csurBasePath, debug, programVersion)

		if 'Scale-up' in csurResourceDict['systemType']:
			#The computeNodeList will be empty if the node did not need to be updated.
			if len(csurResourceDict['componentListDict']['computeNodeList']) == 0:
				cursesThread.insertMessage(['informative', 'The compute node is already up to date; no action taken.'])
			else:
				'''
				For a Scale-up system there will only be two timer threads.  One for the initial initialization 
				and a second for the update.			
				'''
				timerThreadLocation = 1

				computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()

				cursesThread.insertMessage(['informative', 'Phase 2: Updating the compute node components that need to be updated.'])
					
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
				updateVersionInformationFileResult = updateVersionInformationFile(csurResourceDict.copy())

				#Move cursor down for formatting purposes.
				cursesThread.insertMessage(['info', ' '])

				if len(componentProblemDict['Software']) == 0 and len(componentProblemDict['Drivers']) == 0 and len(componentProblemDict['Firmware']) == 0:	
					if not updateVersionInformationFileResult:
						cursesThread.insertMessage(['warning', 'The compute node update completed succesfully, however, the version information file update failed; check the log file for errors and update the file manually.'])
						cursesThread.insertMessage(['info', ' '])
						if computeNodeDict['externalStoragePresent']:
							cursesThread.insertMessage(['final', 'Once the version information file is updated, power cycle the attached storage controller(s) and reboot the system for the changes to take effect.'])
						else:
							cursesThread.insertMessage(['final', 'Once the version information file is updated, reboot the system for the changes to take effect.'])
					else:
						cursesThread.insertMessage(['informative', 'The compute node update completed succesfully.'])
						cursesThread.insertMessage(['info', ' '])
						if computeNodeDict['externalStoragePresent']:
							cursesThread.insertMessage(['final', 'Power cycle the attached storage controller(s) and reboot the system for the changes to take effect.'])
						else:
							cursesThread.insertMessage(['final', 'Reboot the system for the changes to take effect.'])
				else:
					errorMessage = 'The following components encountered errors during the update; check the log file for errors:\n'
					
					if len(componentProblemDict['Software']) != 0:
						errorMessage += 'Software: ' + ', '.join(componentProblemDict['Software'].keys()) + '\n'

					if len(componentProblemDict['Drivers']) != 0:
						errorMessage += 'Drivers: '  + ', '.join(componentProblemDict['Drivers'].keys()) + '\n'

					if len(componentProblemDict['Firmware']) != 0:
						errorMessage += 'Firmware: ' + ', '.join(componentProblemDict['Firmware'].keys()) + '\n'

					if not updateVersionInformationFileResult:
						errorMessage += 'Also, the version information file update failed; check the log file for errors and update the file manually.'

					cursesThread.insertMessage(['error', errorMessage])
		else:
			pass

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
