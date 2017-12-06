#!/usr/bin/python

import spUtils
import subprocess
import logging


'''
This function is used to apply the security patches.
The function returns the variable 'updateStatus' which will be an empty string if there were 
no failures.  Otherwise, the string will contain the name of the patch repository whose update
failed.  This information is also used to determine if the the kernel boot configuration needs 
updating.
'''
def applyPatches(patchDirList):

	logger = logging.getLogger("securityPatchLogger")

	logger.info('Applying security patches from repositories(' + ', '.join(patchDirList) + ').')

	updateStatus = '' 
	count = 0

	#Update OS patches and install kernel patches.
	for dir in patchDirList:

		if 'kernel' in dir:
			command = 'zypper -q -n --non-interactive-include-reboot-patches in ' + dir + ':*'
			logger.debug("command = " + command)
		else:
			command = 'zypper -q -n --non-interactive-include-reboot-patches up ' + dir + ':*'
			logger.debug("command = " + command)
		
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode == 0:
			logger.info("Successfully updated patches from repository " + dir + ".")
			'''
			look at adding further validation.
			'''
		else:
			if count == 0:
				updateStatus += dir
			else:
				updateStatus += ", " + dir
			count += 1
			logger.error(err)
			logger.error("stdout = " + out)
			logger.error("Repository " + dir + ", was unsuccessfully updated.")

	logger.info('Done applying security patches from repositories(' + ', '.join(patchDirList) + ').')

	return updateStatus
#Enddef applyPatches(patchDirList):


#This section is for running the module standalone for debugging purposes.
if __name__ == '__main__':

	#Setup logging.
	logger = logging.getLogger()
	logFile = 'applyPatches.log'

	patchDirList = ['kernelSecurityRPMs', 'OSSecurityRPMs']

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

	updateStatus = applyPatches(patchDirList)

	if updateStatus == '':
                print spUtils.GREEN + "Successfully applied security patches from repositories(" + ', '.join(patchDirList) + ")." + spUtils.RESETCOLORS
	else:
                print spUtils.RED + "Failures were detected during patch installation from repositories(" + ', '.join(patchDirList) + "); check log file for errors." + spUtils.RESETCOLORS
		
