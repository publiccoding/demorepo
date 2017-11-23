#!/usr/bin/python

import subprocess
import logging
import re
from modules.spUtils import (RED, RESETCOLORS)


'''
This function is used to update SUSE_SLES_SAP-release, since it causes issues with 
the update when trying to update. The following message was observed:

Problem: product:SUSE_SLES_SAP-11.3-1.17.x86_64 requires SUSE_SLES_SAP-release = 11.3-1.17, but this requirement cannot be provided
 Solution 1: deinstallation of product:SUSE_SLES_SAP-11.3-1.17.x86_64
 Solution 2: do not install SUSE_SLES_SAP-release-11.3-1.18.x86_64
 Solution 3: break product:SUSE_SLES_SAP-11.3-1.17.x86_64 by ignoring some of its dependencies

Choose from above solutions by number or cancel [1/2/3/c] (c):

This function should not be ran until the SLES osDistLevel has been determined.
Also, before calling this function we should first check to see if the RPM is even installed.
'''
def updateSUSE_SLES_SAPRelease(patchResourceDict, loggerName):

	logger = logging.getLogger(loggerName)

	logger.info("Updating SUSE_SLES_SAP-release.")

	#First we remove the currently installed RPM.
	command = 'rpm -e --nodeps SUSE_SLES_SAP-release'

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        logger.debug("The output of the command (" + command + ") used to remove the SUSE_SLES_SAP-release package was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to remove the SUSE_SLES_SAP-release package.\n" + err)
		print RED + "Unable to remove the SUSE_SLES_SAP-release package; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	try:
		patchBaseDir = (re.sub('\s+', '', patchResourceDict['patchBaseDir'])).rstrip('/')
		osSubDir = re.sub('\s+', '', patchResourceDict['osSubDir'])
		suseSLESSAPReleaseRPM = re.sub('\s+', '', patchResourceDict['suseSLESSAPReleaseRPM'])
		osDistLevel = re.sub('\s+', '', patchResourceDict['osDistLevel'])

		suseSLESSAPReleaseRPM = patchBaseDir + '/' + osDistLevel + '/' + osSubDir + '/' + suseSLESSAPReleaseRPM
	except KeyError as err:
		logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
		print RED + "A resource key was not present in the resource file; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	command = 'zypper -n --non-interactive-include-reboot-patches in ' + suseSLESSAPReleaseRPM

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        logger.debug("The output of the command (" + command + ") used to install the SUSE_SLES_SAP-release RPM was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to install the SUSE_SLES_SAP-release RPM.\n" + err)
		print RED + "Unable to install the SUSE_SLES_SAP-release RPM; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	logger.info("Done updating SUSE_SLES_SAP-release.")

#End removeSUSE_SLES_SAPRelease(patchResourceDict, loggerName):
