#!/usr/bin/python

import spUtils
import subprocess
import logging
import os


'''
This function is used to setup security patch repositories.
The function returns True on success and False on a failure as which time the log
should be consulted.
'''
def configureRepositories(securityPatchDir, patchDirList):

	logger = logging.getLogger("securityPatchLogger")

	logger.info('Configuring security patch repositories.')

	'''
	These are the standard directories in which the patches will always reside by default.
	Note for the kernel xfs issue we will release this with the patchDirs limited to the kernel patches only.
	(patchDirs = ['kernelSecurityRPMs'])
	'''
	#patchDirs = ['kernelSecurityRPMs', 'OSSecurityRPMs']

	#Only create repositories if they do not exist.  Also, make sure they are enabled.
	for dir in patchDirList:
		#The result from this command is used to determine if a repository exists and if so whether or not it is enabled.
		command = 'zypper lr ' + dir + '|grep Enabled'
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		#The returncode is 0 if the repository is succussfully identified.
		if result.returncode == 0:
			if not 'Yes' in out:
				logger.info("Enabling repository " + dir + ", since it was present, but disabled.")
				command = "zypper mr -e " + dir
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode != 0:
					logger.error(err)
					logger.error("stdout = " + out)
					logger.error("Repository " + dir + ", was unsuccessfully enabled.")
					logger.debug("Command used to enable repository was (" + command + ").")
					return False
				else:
					logger.info("Repository " + dir + ", was successfully enabled.")
			else:
				logger.info("No need to enable repository " + dir + ", since it is already present and enabled.")
		else:
			if "Repository '" + dir + "' not found by its alias" in err:
				#By default we strip off trailing '/' for the sake of consistency.
				patchDir = securityPatchDir.rstrip('/') + '/' + dir
				logger.info("Adding repository " + patchDir + ", since it was not present.")
				command = "zypper ar -t plaindir " + patchDir + " " + dir
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode != 0:
					logger.error(err)
					logger.error("stdout = " + out)
					logger.error("Repository " + dir + ", was unsuccessfully added.")
					logger.debug("Command used to add repository was (" + command + ").")
					return False
				else:
					logger.info("Repository " + dir + ", was successfully added.")
			else:
				logger.error(err)
				logger.error("stdout = " + out)
				logger.error("Unable to get repository information using command " + command)
				return False

	logger.info('Done configuring security patch repositories.')

	return True
#End configureRepositories(securityPatchDir):


#This section is for running the module standalone for debugging purposes.
if __name__ == '__main__':

	#Setup logging.
	logger = logging.getLogger()
	logFile = 'configureRepositories.log'

        try:
                open(logFile, 'w').close()
        except IOError:
                print spUtils.RED + "Unable to access " + logFile + " for writing." + spUtils.RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.INFO)
	handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	if configureRepositories("/hp/support/securityPatches"):
                print spUtils.GREEN + "Successfully configured security patch repositories" + spUtils.RESETCOLORS
	else:
                print spUtils.RED + "Unable to configure security patch repositories; check log file for errors." + spUtils.RESETCOLORS
		
