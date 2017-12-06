#!/usr/bin/python


import re
import os
import sys
import subprocess
import shutil
import optparse
import logging


'''
This program is used to install one off patches, e.g. timezone patches, openssl patches, etc.
It is mainly intended for those one off security patches that need to be updated/installed
in between OS patch bundle releases.
'''

#These variables are used for displaying text in color.
RED = '\033[31m'
GREEN = '\033[32m'
RESETCOLORS = '\033[0m'


'''
This class is used to perform the update.
'''
class OneOffPatches:
	def __init__(self, logFile):
                hostname = os.uname()[1]

                #Configure logging
                self.loggerName = hostname + 'Logger'

                handler = logging.FileHandler(logFile)
                logger = logging.getLogger(self.loggerName)
		logger.setLevel(logging.INFO)

                formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
                handler.setFormatter(formatter)
                logger.addHandler(handler)

		#This will be the list of RPMs that are not already installed and that will be applied to the compute node.
		self.rpmsToUpdate = ''

		#This is the name of the patches being installed, e.g. timzone, gcc, openssl, etc.
		self.patchType = None

	#End __init__(self, logFile):


	'''
	This function is used to initialize the program for the update.
	'''
	def initialize(self, executablePath):
		resourceDict = {}

		logger = logging.getLogger(self.loggerName)
		logger.info("Initializing for an OS patch update.")

		#Change into the directory in which the archive was extracted to.
		try:
			os.chdir(executablePath)
		except OSError as err:
			print(RED + "Could not change into the patch archive directory; check the log file for additional information." + RESETCOLORS) 
			logger.error("Could not change into the patch archive directory: " + str(err))
			exit(1)

                '''
                The resourceFile contains information specific to the one off patch update.
                The file name is hardcoded, since it cannot be set ahead of time.
                '''
                resourceFile = 'resourceFiles/oneOffPatchesResourceFile'

                #Get the resource file data and save it to a dictionary (hash).
                try:
                        with open(resourceFile) as f:
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
                                                resourceDict[key] = val.lstrip()
                except IOError as err:
			print(RED + "Unable to open the resource file for reading; check the log file for additional information." + RESETCOLORS)
			logger.error("Unable to open the resource file for reading: " + str(err))
			exit(1)	

		try:
			self.patchType = resourceDict['patchType']
			
			#These are the license files that should be present and that will be installed in /usr/share/doc/hpe.
			gplLicense = resourceDict['gplLicense'] 
			writtenOffer = resourceDict['writtenOffer']
			licenseFileList = [gplLicense, writtenOffer]

			#This is the directory where the license files will copied to.
			hpeLicenseDir = resourceDict['hpeLicenseDir']

			patchArchive = resourceDict['patchArchive']
			patchArchiveMd5sum = resourceDict['patchArchiveMd5sum']
			patchArchiveSubDir = resourceDict['patchArchiveSubDir']

			if not patchArchiveSubDir.endswith('/'):
				patchArchiveSubDir = patchArchiveSubDir + '/'

			supportedOSLevel = resourceDict['supportedOSLevel']
                except KeyError as err:
			print(RED + "A resource key was missing; check the log file for additional information." + RESETCOLORS)
			logger.error("Resource key " + str(err) + " was missing from the resource file.")
			exit(1)	

		#Check that the compute node is at the supported OS level.
		self.__checkOSVersion(supportedOSLevel)
		
		#Check to make sure the license files are present.
		if not os.path.isfile(gplLicense):
			print(RED + "The GPL license file is missing; check the log file for additional information." + RESETCOLORS)
			logger.error("The GPL license file (" + gplLicense + ") is missing.")
			exit(1)	

		if not os.path.isfile(writtenOffer):
			print(RED + "The written offer license file is missing; check the log file for additional information." + RESETCOLORS)
			logger.error("The written offer license file (" + writtenOffer + ") is missing.")
			exit(1)	

		#Check the md5sum of the patch archive to make sure it is not corrupt.
		command = 'md5sum ' + patchArchive
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			print(RED + "Unable to determine the md5sum of the patch archive; check the log file for additional information." + RESETCOLORS)
			logger.error("Unable to determine the md5sum of the patch archive: " + err)
			exit(1)

		patchMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)

		if patchMd5sum != patchArchiveMd5sum:
			print(RED + "The patch archive appears to be corrupt; check the log file for additional information." + RESETCOLORS)
			logger.error("The patch archive appears to be corrupt; its md5sum was: " + patchMd5sum + ", while the md5sum value in the resource file was: " + patchArchiveMd5sum + ".")
			exit(1)

		#Extract the patch RPM archive.
		archiveDir = re.match('(.*)/', patchArchive).group(1)

		command = 'tar -C ' + archiveDir + ' -zxf ' + patchArchive
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			print(RED + "Unable to extract the patch archive; check the log file for additional information." + RESETCOLORS)
			logger.error("Unable to extract the patch archive (" + patchArchive + "): " + err)
			exit(1)

		#Get a list of the RPMs that are to be updated/installed.
		cmd = 'ls ' + patchArchiveSubDir

		result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			print(RED + "Unable to get the list of patches; check the log file for additional information." + RESETCOLORS)
			logger.error("Unable to get the list of patches that were extracted to " + patchArchiveSubDir + ": " + err)
			exit(1)

		rpmList = out.splitlines()

		for rpm in rpmList:
			rpm = rpm.strip()

			rpmName = re.sub('\.x86_64\.rpm', '', rpm)

			cmd = 'rpm -q ' + rpmName

			result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			#This means the RPM was not installed.
			if result.returncode != 0:
				self.rpmsToUpdate += patchArchiveSubDir + rpm + ' '

		#Remove trailing space that was added.
			self.rpmsToUpdate = self.rpmsToUpdate.strip()

		if self.rpmsToUpdate != '':
			#Install the license files.
			self.__installLicenseFiles(hpeLicenseDir, licenseFileList)
		else:
			print(GREEN + "The compute node is already up to date.\n" + RESETCOLORS)
			logger.info("The compute node is already up to date.")
			exit(0)

		logger.info("Done initializing for an OS patch update.")

	#End initialize(self, executablePath, updateType):


	'''
	This function installs the patches.
	'''
	def installPatches(self):
		logger = logging.getLogger(self.loggerName)
		logger.info("Installing the patches: " + self.rpmsToUpdate + ".")

		command = 'rpm -U ' + self.rpmsToUpdate
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			print(RED + "Errors were encountered while installing the patches; check the log file for additional information." + RESETCOLORS)
			logger.error("Errors were encountered while installing the patches: " + err)
			exit(1)

		logger.info("Done installing the patches.")

		print GREEN + "The " + self.patchType + " patches have been successfully installed.\n" + RESETCOLORS

	#End installPatches(self):


	'''
	This function checks to make sure the tha compute node is at 
	the supported OS distribution level for the patch being applied.
	'''
	def __checkOSVersion(self, supportedOSLevel):
		version = None

		logger = logging.getLogger(self.loggerName)
		logger.info("Checking the compute node's OS distribution level.")

		command = "cat /proc/version"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			print(RED + "Unable to get compute node's OS distribution level; check the log file for additional information." + RESETCOLORS)
			logger.error("Unable to get compute node's OS distribution level: " + err)
			exit(1)

		if 'SUSE' in out:
			try:
				with open('/etc/products.d/SUSE_SLES_SAP.prod') as f:
					for line in f:
						if "SUSE_SLES_SAP-release" in line:
							version = re.match("^.*version=\"([0-9]{2}.[0-9]{1})", line).group(1)

							if version != supportedOSLevel:
								print(RED + "The installed SLES Service Pack level is not supported; check the log file for additional information." + RESETCOLORS)
								logger.error("The installed SLES Service Pack level (" + version + ") is not supported.")
								exit(1)

							break
			except (IOError, AttributeError) as err:
				print(RED + "Unable to determine the SLES OS distribution level; check the log file for additional information." + RESETCOLORS)
				logger.error("Unable to determine the SLES OS distribution level: " + str(err))
				exit(1)
		elif 'Red Hat' in out:
			try:
				with open('/etc/redhat-release') as f:
					for line in f:
						if "release" in line:
							version = re.match(".*release\s+([0-9]{1}.[0-9]{1})", line).group(1)

							if version != supportedOSLevel:
								logger.error("The installed RHEL release (" + version + ") is not supported.")
								print(RED + "The installed RHEL release is not supported; check the log file for additional information." + RESETCOLORS)
								exit(1)
							break
			except (IOError, AttributeError) as err:
				print(RED + "Unable to determine the RHEL OS distribution level; check the log file for additional information." + RESETCOLORS)
				logger.error("Unable to determine the RHEL OS distribution level: " + str(err))
				exit(1)
		else:
			print(RED + "The compute node is installed with an unsupported OS; check the log file for additional information." + RESETCOLORS)
			logger.error("The compute node is installed with an unsupported OS: " + out)
			exit(1)

		if version == None:
			print(RED + "Unable to determine the OS distribution level; check the log file for additional information." + RESETCOLORS)
			logger.error("Unable to determine the OS distribution level: " + out)
			exit(1)

		logger.info("Done checking the compute node's OS distribution level.")

	#End __checkOSVersion(self, supportedOSLevel):


	'''
	This function is used to install the license files.
	'''
	def __installLicenseFiles(self, hpeLicenseDir, licenseFileList):
		logger = logging.getLogger(self.loggerName)
		logger.info("Installing the license files: " + ' '.join(licenseFileList) + ".")

		if not os.path.isdir(hpeLicenseDir):
			try:
				os.mkdir(hpeLicenseDir, 0755)
			except OSError as err:
				print(RED + "Unable to create the license directory; check the log file for additional information." + RESETCOLORS)
				logger.error("Unable to create the license directory: " + str(err))
				exit(1)

		for file in licenseFileList:
			try:
				shutil.copy(file, hpeLicenseDir)	
			except IOError as err:
				print(RED + "Unable to install the license files; check the log file for additional information." + RESETCOLORS)
				logger.error("Unable to install the license files: " + str(err))
				exit(1)

		logger.info("Done installing the license files.")

	#End __installLicenseFiles(self, hpeLicenseDir, licenseFileList):


'''
This is the main function which controls the program's flow of execution.
'''
def main(argv):
	#The program can only be ran by root.
	if os.geteuid() != 0:
                print(RED + "You must be root to run this program." + RESETCOLORS)
		exit(1)

        programVersion = '1.0'

        usage = 'usage: %prog [-v]'

        parser = optparse.OptionParser(usage=usage)

        parser.add_option('-v', action='store_true', default=False, help='This option is used to display the programs\'s version.')

        (options, args) = parser.parse_args()

	executableName = os.path.basename(argv[0])

	logFile = executableName + ".log"

	if os.path.isfile(logFile):
		try:
			os.remove(logFile)
		except OSError as err:
			print(RED + "Unable to remove the previous log file (" + logFile + "); fix the problem and try again.\n" + str(err) + RESETCOLORS)
			exit(1)

	#This is the location of where the archive was extracted to, which is also the scripts location.
	executablePath = re.sub(executableName, '', os.path.abspath(sys.argv[0]))

        if options.v:
                print(executableName + ' ' + programVersion)
                exit(0)

	#Instantiate the main class that will be used to perform the update.
	oneOffPatches = OneOffPatches(logFile)

	oneOffPatches.initialize(executablePath)

	oneOffPatches.installPatches()

#End main(argv):

main(sys.argv)
