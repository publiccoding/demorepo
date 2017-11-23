#!/usr/bin/python

import subprocess
import logging
import re


'''
This function is used to install the HPE SAP HANA patch bundle release RPM.
It takes either no argument or 'os' or 'kernel', which are used to point to the 
correct RPM.
'''
def installReleaseRPM(patchResourceDict, *args):

	logger = logging.getLogger("patchLogger")

	logger.info("Installing the patch bundle release RPM.")

	patchType = ''

	if len(args) == 1:
		patchType = args[0]

	try:
		patchBaseDir = (re.sub('\s+', '', patchResourceDict['patchBaseDir'])).rstrip('/')
		releaseRPMSubDir = re.sub('\s+', '', patchResourceDict['releaseRPMSubDir'])
		patchBundleReleaseRPM = re.sub('\s+', '', patchResourceDict['patchBundleReleaseRPM'])
		osDistLevel = re.sub('\s+', '', patchResourceDict['osDistLevel'])

		if patchType == '':
			patchBundleReleaseRPM = patchBaseDir + '/' + osDistLevel + '/' + releaseRPMSubDir + '/' + patchBundleReleaseRPM
		else:
			patchBundleReleaseRPM = patchBaseDir + '/' + osDistLevel + '/' + releaseRPMSubDir + '/' + patchType + '/' + patchBundleReleaseRPM
	except KeyError as err:
		logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
		return 'Failure'

	command = 'rpm -Uvh --force ' + patchBundleReleaseRPM

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        logger.debug("The output of the command (" + command + ") used to install the patch bundle release RPM was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to install the patch bundle release RPM.\n" + err)
                return 'Failure'

	logger.info("Done installing the patch bundle release RPM.")

	return 'Success'

#End installReleaseRPM(patchResourceDict, *args):
