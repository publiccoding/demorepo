#!/usr/bin/python

from spUtils import RED, RESETCOLORS
import subprocess
import logging
import os


'''
This function is used to setup the patch repositories.
'''
def configureRepositories(patchDirList, loggerName):
	
	logger = logging.getLogger(loggerName)

	logger.info('Configuring patch repositories.')

	logger.debug("The patch directory list is: " + str(patchDirList))

	'''
	If a repository already exists then we remove and recreate it in case it has a different configuration.
	Otherwise, if the repository does not already exist it will be created.
	'''	
	for dir in patchDirList:
		#Use the end of the patch directory path as the name for the repository.
		repositoryName = dir.split('/').pop()

		#The result from this command is used to determine if a repository exists.
		command = 'zypper lr ' + repositoryName
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to list repository '" + repositoryName + "' was: " + out.strip())

		#The returncode is 0 if the repository is succussfully identified.
		if result.returncode == 0:
			logger.info("Removing repository " + repositoryName + ", since it was present.")
			command = "zypper rr " + repositoryName
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to remove repository '" + repositoryName + "' was: " + out.strip())

			if result.returncode != 0:
				logger.error("The repository " + repositoryName + ", could not be removed.\n" + err)
				print RED + "Unable to remove existing repositories; check the log file for errors; exiting program execution." + RESETCOLORS
				exit(1)
			else:
				logger.info("The repository " + repositoryName + ", was successfully removed.")
		elif "Repository '" + repositoryName + "' not found by its alias" in err:
			logger.info("The repository " + repositoryName + ", was not found to be present.")
		else:
			logger.error("Unable to get repository information using command " + command + "\n" + err)
			print RED + "Unable to get repository information; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)

		#Create repositories.
		logger.info("Adding repository " + repositoryName + ".")
		command = "zypper ar -t plaindir " + dir + " " + repositoryName
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to add repository '" + repositoryName + "' was: " + out.strip())

		if result.returncode != 0:
			logger.error("The repository " + repositoryName + ", was unsuccessfully added.\n" + err)
			print RED + "Unable to to add repositories; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)
		else:
			logger.info("The repository " + repositoryName + ", was successfully added.")

	logger.info('Done configuring patch repositories.')

#End configureRepositories(patchDirList, loggerName):


'''
#This section is for running the module standalone for debugging/testing purposes.  Uncomment to use.
if __name__ == '__main__':

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = 'configureRepositories.log'

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

	patchDirList = ['/hp/support/patches/SLES_SP3/kernelRPMs', '/hp/support/patches/SLES_SP3/OSRPMs']

	configureRepositories(patchDirList, loggerName)
'''
