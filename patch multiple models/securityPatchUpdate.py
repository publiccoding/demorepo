#!/usr/bin/python


import logging
import os
import optparse
import signal
import re
import subprocess
from modules.spUtils import (RED, GREEN, PURPLE, BOLD, UNDERLINE, RESETCOLORS, signal_handler)
from modules.preUpdate import (checkOSVersion, setPatchDirectories, checkSystemConfiguration, checkOSVersion, checkDiskSpace)
from modules.postUpdate import (buildDeadmanDriver, updateFusionIO)
from modules.configureRepository import configureRepositories
from modules.updateZyppConf import updateZyppConf
from modules.applyPatches import applyPatches
from modules.createBootloaderConfigFile import configureBootLoader
from modules.installReleaseRPM import installReleaseRPM
from modules.issues import updateSUSE_SLES_SAPRelease


'''
This function is used to initialize the program.  It performs the following:
	1.  Ensures that the program is being ran as root.
	2.  Removes any old log files if they exist.  This would occur if the program has already been ran previously.
	3.  Sets up logging.
	4.  Ensures that the patches being installed are for the correct current OS that is installed.
	5.  Calls a function to update /etc/zypp/zypp.conf.
	6.  Calls a function to set up the repositories.
	7.  Returns a dictionary (hash) containing the resource files resources.
	8.  Ensures that the root file system has at least 2GB of space.
'''
def init(applicationResourceFile):
	#The program can only be ran by root.
	if os.geteuid() != 0:
		print RED + "You must be root to run this program." + RESETCOLORS
		exit(1)

	usage = 'usage: %prog [[-a] [-k] [-o] [-p] -d] [-h]'

	parser = optparse.OptionParser(usage=usage)

        parser.add_option('-a', action='store_true', default=False, help='This option will result in the application of both OS and Kernel patches.')
	parser.add_option('-d', action='store_true', default=False, help='This option is used when problems are encountered and additional debug information is needed.')
        parser.add_option('-k', action='store_true', default=False, help='This option will result in the application of Kernel patches.')
        parser.add_option('-o', action='store_true', default=False, help='This option will result in the application of OS patches.')
        parser.add_option('-p', action='store_true', default=False, help='This option is used to perform the post update tasks.')

	(options, args) = parser.parse_args()

	if (options.a and options.k) or (options.a and options.o) or (options.k and options.o) or (options.a and options.p) or (options.o and options.p) or (options.k and options.p):
		parser.error("Options -a, -k, -o and -p are mutually exclusive.")

	if not options.a and not options.k and not options.o and not options.p:
		parser.error("At least one of the following options is required: -a, -k, -o or -p.")

	if options.p:
		print GREEN + "Phase 1: Initializing for the post system update." + RESETCOLORS
	else:
		print GREEN + "Phase 1: Initializing for the system update." + RESETCOLORS

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

	#Get the application's log file information.
	try:
		logBaseDir = (re.sub('\s+', '', patchResourceDict['logBaseDir'])).rstrip('/')
                patchApplicationLog = re.sub('\s+', '', patchResourceDict['patchApplicationLog'])
                patchApplicationLog = logBaseDir + '/' + patchApplicationLog
	except KeyError as err:
		print RED + "The resource key (" + str(err) + ") was not present in the resource file; exiting program execution." + "\n" + RESETCOLORS
		exit(1)

	if not options.p:	
		try:
			#Always start with an empty log directory when performing a new update.
			logList = os.listdir(logBaseDir)
		
			for log in logList:
				os.remove(logBaseDir + '/' + log)
		except Error as err:
			print RED + "Unable to remove old logs in " + logBaseDir + "; exiting program execution.\n" + str(err) + "\n" + RESETCOLORS
			exit(1)

	#Configure logging.
	handler = logging.FileHandler(patchApplicationLog)

	logger = logging.getLogger("patchLogger")

	if options.d:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	if options.p:
		return patchResourceDict

	#Check available disk space.  There needs to be at least 2G free.
	checkDiskSpace()

	#Check and get the OS distribution information.
	osDistLevel = checkOSVersion(patchResourceDict.copy())

	patchResourceDict['osDistLevel'] = osDistLevel

	#Check if system has FusionIO cards for log and/or the system is a Serviceguard system.
	postUpdateRequired = ''

	if options.a or options.k:
		postUpdateRequired = checkSystemConfiguration(patchResourceDict)

	patchResourceDict['postUpdateRequired'] = postUpdateRequired

	'''
	If OS patches are being installed then update SUSE_SLES_SAP-release first as it causes issues
	when trying to update with the rest of the patches.
	'''	
	if options.a or options.o:
		#Fist check to see if the SUSE_SLES_SAP-release RPM is installed.
		command = 'rpm -q SUSE_SLES_SAP-release'

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode == 0:
			updateSUSE_SLES_SAPRelease(patchResourceDict.copy())
		else:
			if 'package SUSE_SLES_SAP-release is not installed' not in out:
				print RED + "Unable to determine if the SUSE_SLES_SAP-release RPM is installed; " + out + "; exiting program execution." + RESETCOLORS
				exit(1)

	#Check and get the patch directories.
	patchDirList = setPatchDirectories(patchResourceDict.copy())

	#Configure the necessary patch repositories.
        configureRepositories(patchDirList[:])

	#Need to extract and save the repository names, which will be used by zypper when updating the system.
	repositoryList = []
	for dir in patchDirList:
		repositoryList.append(dir.split('/').pop())

	patchResourceDict['repositoryList'] = repositoryList

	#Update zypp.conf so that the current kernel and the new kernel are both installed.
        updateZyppConf()

	return patchResourceDict

#End init()

def main():
	applicationResourceFile = '/hp/support/patches/resourceFiles/patchResourceFile'

	patchResourceDict = init(applicationResourceFile)

	logger = logging.getLogger("patchLogger")

	options = patchResourceDict['options']

	if not options.p:
		print GREEN + "Phase 2: Updating system with patches." + RESETCOLORS
		
		#Set traps so that the software update is not interrupted by the user.
                original_sigint_handler = signal.getsignal(signal.SIGINT)
                original_sigquit_handler = signal.getsignal(signal.SIGQUIT)
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGQUIT, signal_handler)
	
		#Apply patches to the system based on option(s) selected.
		applyPatches(patchResourceDict['repositoryList'])

		#Restore the signals back to their defaults.
                signal.signal(signal.SIGINT, original_sigint_handler)
                signal.signal(signal.SIGQUIT, original_sigquit_handler)

		updateTaskStatusDict = {}

		#Configure the boot loader for the new kernel if option 'a' or 'k' were selected.
		if options.a or options.k:
			print GREEN + "Phase 3: Updating the system's bootloader." + RESETCOLORS
			updateTaskStatusDict['configureBootLoader'] = configureBootLoader() 

		#Install the patch bundle release RPM.
		print GREEN + "Phase 4: Installing the patch bundle release RPM." + RESETCOLORS

		if options.a:
			updateTaskStatusDict['installReleaseRPM'] = installReleaseRPM(patchResourceDict.copy())
		elif options.k:
			updateTaskStatusDict['installReleaseRPM'] = installReleaseRPM(patchResourceDict.copy(), 'kernel')
		elif options.o:
			updateTaskStatusDict['installReleaseRPM'] = installReleaseRPM(patchResourceDict.copy(), 'os')

		taskFailureList = ''

		#Now check if any of the update tasks failed and print hte appropriate message.
		for key, value in updateTaskStatusDict.iteritems():
			if value == 'Failure':
				if taskFailureList == '':
					taskFailureList += key
				else:
					taskFailureList += ', ' + key

		if taskFailureList == '':
			if patchResourceDict['postUpdateRequired'] == 'yes':
				print GREEN + "\nThe system update has completed.  Reboot the system for the changes to take affect.\n" + RESETCOLORS
				print PURPLE + BOLD + UNDERLINE + "Make sure to run the program again with the '-p' option after the system reboots to complete the update procedure!\n" + RESETCOLORS 
			else:
				print GREEN + "\nThe system update has successfully completed.  Reboot the system for the changes to take affect.\n" + RESETCOLORS
		else:
			if patchResourceDict['postUpdateRequired'] == 'yes':
				print RED + BOLD + "\nThe system update failed to complete successfully.  Address the failed update tasks(" + taskFailureList + ") and then reboot the system for the changes to take affect.\n" + RESETCOLORS
				print PURPLE + BOLD + UNDERLINE + "Make sure to run the program again with the '-p' option after the system reboots to complete the update procedure!\n" + RESETCOLORS 
			else:
				print RED + BOLD + "\nThe system update failed to complete successfully.  Address the failed update tasks(" + taskFailureList + ") and then reboot the system for the changes to take affect.\n" + RESETCOLORS
	else:
		'''
		Get the post update resume log, which contains information for the post update tasks.
		The following is a list of variables currently found in the post update resume log:
			isServiceguardSystem = 'yes or no'
			isFusionIOSystem = 'yes or no'
			firmwareUpdateRequired = 'yes or no'
			busList = '8c:00.0 8d:00.0 87:00.0 88:00.0'
		'''
		try:
			logBaseDir = (re.sub('\s+', '', patchResourceDict['logBaseDir'])).rstrip('/')
			postUpdateResumeLog = re.sub('\s+', '', patchResourceDict['postUpdateResumeLog'])
			postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog
		except KeyError as err:
			logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
			print RED + "The resource key for the post update resume log was not present in the resource file; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)

		resumeDict = {}

		try:
			with open(postUpdateResumeLog) as f:
				for line in f:
					line = line.strip()
					#Remove quotes.
					line = re.sub('[\'"]', '', line)
					
					#Ignore commented and blank lines.
					if len(line) == 0 or re.match("^#", line):
						continue
					else:
						(key, val) = line.split('=')
						key = re.sub('\s+', '', key)
						resumeDict[key] = val.lstrip()
		except IOError as err:
			logger.error("Unable to get the post update information from resume log.\n" + str(err))
			print RED + "Unable to get the post update information from resume log; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)

		#This is used for the phase numbering.  The count starts at two, since one was already used for the initialization message.
		count = 2

		#This is used to keep track of post update task completion status.

		postUpdateTaskStatusDict = {}

		if 'isServiceguardSystem' in resumeDict:
			if resumeDict['isServiceguardSystem'] == 'yes':
				print GREEN + "Phase " + str(count) + ": Building and installing the deadman driver." + RESETCOLORS
				postUpdateTaskStatusDict['buildDeadmanDriver'] = buildDeadmanDriver() 
				count += 1

		if 'isFusionIOSystem' in resumeDict:
			if resumeDict['isFusionIOSystem'] == 'yes':
				if resumeDict['firmwareUpdateRequired'] == 'yes':
					print GREEN + "Phase " + str(count) + ": Updating FusionIO firmware, driver, and software." + RESETCOLORS
					postUpdateTaskStatusDict['updateFusionIO'] = updateFusionIO(patchResourceDict.copy(), firmwareUpdateRequired = resumeDict['firmwareUpdateRequired'], busList = resumeDict['busList']) 
				else:
					print GREEN + "Phase " + str(count) + ": Updating FusionIO driver and software." + RESETCOLORS
					postUpdateTaskStatusDict['updateFusionIO'] = updateFusionIO(patchResourceDict.copy(), firmwareUpdateRequired = resumeDict['firmwareUpdateRequired']) 

		taskFailureList = ''

		for key, value in postUpdateTaskStatusDict.iteritems():
			if value == 'Failure':
				if taskFailureList == '':
					taskFailureList += key
				else:
					taskFailureList += ', ' + key

		if taskFailureList == '':
			print GREEN + "\nThe system update has successfully completed.  Reboot the system for the changes to take affect.\n" + RESETCOLORS
		else:
			print RED + BOLD + "\nThe system update failed to complete successfully.  Address the failed post update tasks(" + taskFailureList + ") and then reboot the system for the changes to take affect.\n" + RESETCOLORS

#End main()


#####################################################################################################
# Main program starts here.
#####################################################################################################
main()
