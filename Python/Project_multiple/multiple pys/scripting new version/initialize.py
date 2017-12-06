import logging
import os
import subprocess
import re
from csurUtils import (RED, GREEN, RESETCOLORS)
from fusionIOUtils import checkFusionIOFirmwareUpgradeSupport


class Initialize:
	def __init__(self):
		self.version = 'v1.0'
		self.versionLength = len(self.version)
		self.title = "SAP HANA CSUR Update Application"
		self.titleLength = len(self.title)
		self.author = "Bill Neumann - SAP HANA CoE"
		self.authorLength = len(self.author)
		self.copyright = '(c) Copyright 2016 Hewlett Packard Enterprise Development LP'
		self.copyrightLength = len(self.copyright)
		
		self.systemType = ''
	
	def __printHeader(self):
		print "+" + "-"*78 + "+"
		print "|" + self.title + " "*(78-self.titleLength) + "|"
		print "|" + self.version + " "*(78-self.versionLength) + "|"
		print "|" + self.author + " "*(78-self.authorLength) + "|"
		print "|" + self.copyright + " "*(78-self.copyrightLength) + "|"
		print "+" + "-"*78 + "+"
		print "\n"

	#End printHeader():


	def __getConfigurationType(self):

		while(1):
			print "\t1. Scale-up"
			print "\t2. Scale-out"
				
			selection = raw_input("Select the system type to be updated: ")

			if selection == '1':
				self.systemType = 'Scale-up'
				break
			elif selection == '2':
				self.systemType = 'Scale-out'
				break
			else:
				print "An invalid selection was made; please try again."
			
	#End getConfigurationType():


	def getSystemSelectionData(self):
		pass


	def init(self, csurBasePath, loggerName):

		if os.geteuid() != 0:
			print RED + "You must be root to run this program; exiting program execution.\n" + RESETCOLORS
			exit(1)

		usage = 'usage: %prog [[-d] [-h] [-v]]'

		parser = optparse.OptionParser(usage=usage)

		parser.add_option('-d', action='store_true', default=False, help='This option is used when problems are encountered and additional debug information is needed.')
		parser.add_option('-v', action='store_true', default=False, help='This option is used to display the application\'s version.')

		(options, args) = parser.parse_args()

		self.__printHeader()

		print GREEN + "Phase 1: Initializing for the system update.\n" + RESETCOLORS 

		self.__getConfigurationType()
		
		csurResourceDict = {}

		#Save the csur base path to the csur resource dict as it will be needed later.
		csurResourceDict['csurBasePath'] = csurBasePath

		csurAppResourceFile = csurBasePath + '/resourceFiles/csurAppResourceFile'
		csurDataResourceFile = csurBasePath + '/resourceFiles/csurDataResourceFile'

		#Get csur application's resource file data and save it to a dictionary (hash).
		try:
			with open(csurAppResourceFile) as f:
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
						csurResourceDict[key] = val.lstrip()
		except IOError as err:
			print RED + "Unable to access the application's resource file " + csurAppResourceFile + "; exiting program execution.\n" + str(err) + "\n" + RESETCOLORS
			exit(1)

		#Get the csur's resource data (software, firmware, drivers) and save it to a list (array). 
		try:
			with open(csurDataResourceFile) as f:
				csurData = f.read().splitlines()
		except IOError:
			print RED + "Unable to open " + csurDataResourceFile + " for reading; exiting program execution.\n" + RESETCOLORS
			exit(1)

		csurResourceDict['csurData'] = csurData

		#Get the application's log file information.
		try:
			logBaseDir = csurBasePath + '/log'
			csurApplicationLog = logBaseDir + '/' + csurResourceDict['csurApplicationLog']
		except KeyError as err:
			print RED + "The resource key (" + str(err) + ") was not present in the resource file; exiting program execution.\n" + RESETCOLORS
			exit(1)

		try:
			#Always start with an empty log directory when performing a new update.
			logList = os.listdir(logBaseDir)

			for log in logList:
				os.remove(logBaseDir + '/' + log)
		except OSError as err:
			print RED + "Unable to remove old logs in " + logBaseDir + "; exiting program execution.\n" + str(err) + "\n" + RESETCOLORS
			exit(1)


		#Configure logging

		handler = logging.FileHandler(csurApplicationLog)

		logger = logging.getLogger(loggerName)

		if options.d:
			logger.setLevel(logging.DEBUG)
		else:
			logger.setLevel(logging.INFO)

		formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
		handler.setFormatter(formatter)
		logger.addHandler(handler)

		#Get the system's OS distribution version information.
		command = "cat /proc/version"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		#Change version information to lowercase before checking for OS type.
		versionInfo = out.lower()
		
		if result.returncode != 0:
			logger.error("Unable to get the system's OS distribution version information.\n" + str(err))
			print RED + "Unable to get the system's OS distribution version information; check the log file for errors; exiting program execution.\n" + RESETCOLORS
			exit(1)

		if 'suse' in versionInfo:
			OSDist = 'SLES'
			command = "cat /etc/SuSE-release"
		else:
			OSDist = 'RHEL'
			command = "cat /etc/redhat-release"

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error("Unable to get the system's OS distribution level.\n" + str(err))
			print RED + "Unable to get the system's OS distribution level; check the log file for errors; exiting program execution.\n" + RESETCOLORS
			exit(1)
		else:
			releaseInfo = out.replace('\n', ' ')

			if OSDist == 'SLES':
				slesVersion = re.match('.*version\s*=\s*([1-4]{2})', releaseInfo, re.IGNORECASE).group(1)
				slesPatchLevel = re.match('.*patchlevel\s*=\s*([1-4]{1})', releaseInfo, re.IGNORECASE).group(1)
				osDistLevel = OSDist + slesVersion + '.' + slesPatchLevel
			else:
				rhelVersion = re.match('.*release\s+([6-7]{1}.[0-9]{1}).*', releaseInfo, re.IGNORECASE).group(1)
				osDistLevel = OSDist + rhelVersion

		csurResourceDict['osDistLevel'] = osDistLevel

		if osDistLevel not in csurResourceDict['supportedDistributionLevels']:
			logger.error("The system's OS distribution level (" + osDistLevel + ") is not supported by this CSUR bundle.")
			logger.info("The supported OS distribution levels are (" + csurResourceDict['supportedDistributionLevels'] + ").")
			print RED + "The system's OS distribution level is not supported by this CSUR bundle; check the log file for errors; exiting program execution.\n" + RESETCOLORS
			exit(1)

		#Get system model.
		command = "dmidecode -s system-product-name"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error("Unable to get the system's model information.\n" + str(err))
			print RED + "Unable to get the system's model information; check the log file for errors; exiting program execution.\n" + RESETCOLORS
			exit(1)
			
		systemModel = (re.match('[a-z,0-9]+\s+(.*)', out, re.IGNORECASE).group(1)).replace(' ', '')

		if systemModel not in csurResourceDict['supportedComputeNodeModels']:
			logger.error("The system's model (" + systemModel + ") is not supported by this CSUR bundle.")
			logger.info("The supported supported models are (" + csurResourceDict['supportedComputeNodeModels'] + ").")
			print RED + "The system's model is not supported by this CSUR bundle; check the log file for errors; exiting program execution.\n" + RESETCOLORS
			exit(1)

		csurResourceDict['systemModel'] = systemModel

		#FusionIO should only be installed on Gen 1.0 Scale-up systems.
		if systemModel == 'DL580G7' or systemModel == 'DL980G7':
			fioStatus = '/usr/bin/fio-status'

			if os.path.exists(fioStatus):
				command = fioStatus + ' -c'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to determine the number of FusionIO cards was: " + out.strip())

				if result.returncode == 0:
					if out.strip() == 0:
						logger.info("fio-status was present, but it appears the system does not have any FusionIO cards.\n")
						csurResourceDict['FusionIOSubsystem'] = 'no'
					else:
						csurResourceDict['FusionIOSubsystem'] = 'yes'
				else:
					logger.error("Unable to determine the number of FusionIO cards installed.\n" + str(err))
					print RED + "Unable to determine the number of FusionIO cards installed; check the log file for errors; exiting program execution.\n" + RESETCOLORS
					exit(1)
			else:
				logger.info("The compute node was a " + systemModel + ", however its FusionIO status could not be determined (/usr/bin/fio-status missing).")
				csurResourceDict['FusionIOSubsystem'] = 'no'

			if csurResourceDict['FusionIOSubsystem'] == 'yes':
				#Get the currently used kernel and processor type, which is used as part of the FusionIO driver RPM name.
				command = 'uname -r'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to get the currently used kernel was: " + out.strip())

				if result.returncode != 0:
					logger.error("Unable to get the system's current kernel information.\n" + err)
					print RED + "Unable to get the system's current kernel information; check the log file for errors; exiting program execution.\n" + RESETCOLORS
				else:
					kernel = out.strip()
					csurResourceDict['kernel'] = kernel
				
				command = 'uname -p'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to get the system's processor type was: " + out.strip())

				if result.returncode != 0:
					logger.error("Unable to get the system's processor type.\n" + err)
					print RED + "Unable to get the system's processor type; check the log file for errors; exiting program execution.\n" + RESETCOLORS
				else:
					processorType = out.strip()
					csurResourceDict['processorType'] = processorType

				if not checkFusionIOFirmwareUpgradeSupport(csurResourceDict['fusionIOFirmwareVersionList'], loggerName):
					print RED + "The fusionIO firmware is not at a supported version for an automatic upgrade; upgrade the firmware manually and try again; exiting program execution.\n" + RESETCOLORS

		return csurResourceDict

	#End init()
