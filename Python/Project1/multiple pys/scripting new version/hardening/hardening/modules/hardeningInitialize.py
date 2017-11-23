import logging
import re
import os
import datetime
import subprocess
from hardeningUtils import (RED, RESETCOLORS)


'''
This class is used to initialize the program before hardening the system.
'''
class Initialize:
	'''
	This function prints the initial application header.
	'''
	def __printHeader(self, programVersion):
		version = 'Version ' + programVersion
		versionLength = len(version)
		title = "SAP HANA CSUR Hardening Application"
		titleLength = len(title)
		author = "Bill Neumann - SAP HANA CoE"
		authorLength = len(author)
		copyright = '(c) Copyright 2017 Hewlett Packard Enterprise Development LP'
		copyrightLength = len(copyright)

                print("+" + "-"*65 + "+")
                print("|" + title + " "*(65-titleLength) + "|")
                print("|" + version + " "*(65-versionLength) + "|")
                print("|" + author + " "*(65-authorLength) + "|")
                print("|" + copyright + " "*(65-copyrightLength) + "|")
                print("+" + "-"*65 + "+")

	#End __printHeader(self):

	
	'''
	This is the main function that is called to do the program initialization.
	It returns the hardeningResourceDict which contains all the information gathered during
	initialization that is needed to harden the system.
	'''
	def init(self, hardeningBasePath, debug, programVersion):
		hardeningResourceDict = {}
		#Save the hardening base path to the csur resource dict as it will be needed later.
		hardeningResourceDict['hardeningBasePath'] = hardeningBasePath

		self.__printHeader(programVersion)

		print("Phase 1: Initializing the system in preparation for hardening.")

		'''
		The hardeningResourceFile contains information specific to the program, e.g. supported OS, etc.
		The file name is hardcoded, since it cannot be set ahead of time.
		'''
		hardeningResourceFile = hardeningBasePath + '/resourceFiles/hardeningResourceFile'

		#Get program's resource file data and save it to a dictionary (hash).
		try:
			with open(hardeningResourceFile) as f:
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
						hardeningResourceDict[key] = val.lstrip()
		except IOError as err:
			print(RED + "Unable to open the program's resource file (" + hardeningResourceFile + ") for reading; exiting program execution.\n" + str(err) + RESETCOLORS)
			exit(1)

		'''
		Configure logging; a new log directory is created each time the program is ran
		so that previous log data is kept separate.
		'''
		currentLogDir = datetime.datetime.now().strftime("Date_%d%b%Y_Time_%H:%M:%S")
		logBaseDir = hardeningBasePath + '/log/' + currentLogDir + '/'

		hardeningResourceDict['logBaseDir'] = logBaseDir

		try:
			os.mkdir(logBaseDir)
		except OSError as err:
			print(RED + 'Unable to create the current log directory ' + logBaseDir + '; exiting program execution.\n' + str(err) + RESETCOLORS)
			exit(1)

		try:
			hardeningLog = hardeningResourceDict['hardeningLog']
		except KeyError as err:
			print(RED + "The resource key (" + str(err) + ") was not present in the program's resource file " + hardeningResourceFile + "; exiting program execution." + RESETCOLORS)
			exit(1)

		hardeningLog = logBaseDir + hardeningLog
		hardeningHandler = logging.FileHandler(hardeningLog)

		loggerName = 'hardeningLogger'
		hardeningResourceDict['loggerName'] = loggerName

		logger = logging.getLogger(loggerName)

		if debug:
			logger.setLevel(logging.DEBUG)
		else:
			logger.setLevel(logging.INFO)

		formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
		hardeningHandler.setFormatter(formatter)
		logger.addHandler(hardeningHandler)

		hardeningResourceDict['osDistLevel'] = self.__checkOSVersion(hardeningResourceDict.copy())

		return hardeningResourceDict

	#End init(self, hardeningBasePath, debug, programVersion):


	'''
	This function is used to check what OS is installed and that it is a supported OS
	at the correct service pack level.  Currently Red Hat is not supported.
	The osDistLevel is returned.
	'''
	def __checkOSVersion(self, hardeningResourceDict):

		logger = logging.getLogger(hardeningResourceDict['loggerName'])

		logger.info("Checking and getting the system's OS distribution information.")

		command = "cat /proc/version"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the system's OS distribution information was: " + out.strip())

		if result.returncode != 0:
			logger.error("Unable to get system's OS type.\n" + err)
			print(RED + "Unable to get system's OS type; check the log file for errors; exiting program execution." + RESETCOLORS)
			exit(1)

		if 'SUSE' in out:
			'''
			Check to make sure that the OS is SLES4SAP and that it is a supported service pack level.
			The file name changed on SLES 12.1 from '/etc/products.d/SUSE_SLES_SAP.prod' to '/etc/products.d/SLES_SAP.prod'.
			'''
			if os.path.isfile('/etc/products.d/SUSE_SLES_SAP.prod'):
				productFile = '/etc/products.d/SUSE_SLES_SAP.prod'
			elif os.path.isfile('/etc/products.d/SLES_SAP.prod'):
				productFile = '/etc/products.d/SLES_SAP.prod'
			else:
				logger.error("Unable to determine the SLES OS type, since the SLES product file (SUSE_SLES_SAP.prod or SLES_SAP.prod) was missing from the '/etc/products.d' directory.")
				print(RED + "Unable to determine the SLES OS type; check the log file for errors; exiting program execution." + RESETCOLORS)
				exit(1)

			try:
				with open(productFile) as f:
					for line in f:
						line = line.strip()

						if "SLES_SAP-release" in line:
							version = re.match("^.*version=\"([0-9]{2}.[0-9]{1}).*", line).group(1)

							if version in hardeningResourceDict: #Example entry is: 11.4 = SLES_SP4
								osDistLevel = (hardeningResourceDict[version]).lstrip()
							else:
								logger.error("The SLES Service Pack level (" + version + ") installed is not supported.")
								print(RED + "The SLES Service Pack level installed is not supported; check the log file for additional information; exiting program execution." + RESETCOLORS)
								exit(1)
							break
			except IOError as err:
				logger.error("Unable to determine the SLES OS type.\n" + str(err))
				print(RED + "Unable to determine the SLES OS type; check the log file for errors; exiting program execution." + RESETCOLORS)
				exit(1)
		elif 'Red Hat' in out:
			logger.error("The compute node is installed with Red Hat, which is not yet supported.")
			print(RED + "The compute node is installed with Red Hat, which is not yet supported; exiting program execution." + RESETCOLORS)
			exit(1)
		else:
			logger.error("The compute node is installed with an unsupported OS.")
			print(RED + "The compute node is installed with an unsupported OS; exiting program execution." + RESETCOLORS)
			exit(1)

		logger.info("Done checking and getting the system's OS distribution information.")

		logger.debug("The OS distribution level was determined to be: " + osDistLevel)

		return osDistLevel

	#End __checkOSVersion(self, hardeningResourceDict):

#End class Initialize:
