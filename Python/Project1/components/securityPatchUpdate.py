#!/usr/bin/python

import logging
import optparse
import os
import subprocess

import spUtils
from configureRepository import configureRepositories

from components.updateZyppConf import updateZyppConf

'''
This function is used to initialize the program.  It performs the following:
	1.  Ensures that the program is being ran as root.
	2.  Removes any old log files if they exist.  This would occur if the program has already been ran previously.
	3.  Sets up logging.
	4.  Ensures that the patches being installed are for the correct current OS that is installed.
'''
def init(patchDirectoryList):
	applicationLogFile = '/hp/support/log/securityPatchLog.log'
	zyppConfUpdateLogFile = '/hp/support/log/zyppConfUpdateLog.log'
	securityPatchBaseDir = '/hp/support/securityPatches'

	#The program can only be ran by root.
	if os.geteuid() != 0:
		print spUtils.RED + "You must be root to run this program." + spUtils.RESETCOLORS
		exit(1)

	usage = 'usage: %prog [-d | -h]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-d', action='store_true', default=False, help='This option is used to collect debug information', metavar=' ')

	(options, args) = parser.parse_args()

	#Always start with a new log file.
	try:
		if os.path.isfile(applicationLogFile):
			os.remove(applicationLogFile)
		else:
			open(applicationLogFile, 'w').close()
	except IOError:
		print spUtils.RED + "Unable to access " + applicationLogFile + " for writing.\n" + spUtils.RESETCOLORS
		exit(1)

	handler = logging.FileHandler(applicationLogFile)

	if options.d:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	#Check to see what OS is installed. If it is not SLES then it must be RHEL
	command = "cat /proc/version|grep -i suse"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get system OS type.\n" + err + "\n; exiting program execution.")
		print spUtils.RED + "Unable to get system OS type; check log file for errors." + spUtils.RESETCOLORS
		exit(1)
		
	if result.returncode == 0:
		OSDist = 'SLES'
		command = "cat /etc/SuSE-release | grep PATCHLEVEL|awk '{print $3}'"
	else:
		OSDist = 'RHEL'
		command = "cat /etc/redhat-release | egrep -o \"[1-9]{1}\.[0-9]{1}\""

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get OS distribution level.\n" + err + "\n; exiting program execution.")
		print spUtils.RED + "Unable to get OS distribution level; check log file for errors." + spUtils.RESETCOLORS
		exit(1)
	else:
                if OSDist == 'SLES':
                        OSDistLevel = OSDist + '_SP' + out.strip()
                else:
                        OSDistLevel = OSDist + '_Release_' + out.strip()

	securityPatchDir = securityPatchBaseDir + '/' + OSDistLevel

	if not os.path.exists(securityPatchDir):
		logger.error("This is not a " + OSDistLevel + " installed system or the patch directory (" + securityPatchDir +") is missing; exiting program execution.")
		print spUtils.RED + "This is not a " + OSDistLevel + " installed system or the patch directory (" + securityPatchDir +") is missing; exiting program execution.\n" + spUtils.RESETCOLORS
		exit(1)

        if configureRepositories(securityPatchBaseDir, patchDirectoryList[:]):
                logger.info("Successfully configured security patch repositories.")
        else:
                print spUtils.RED + "Unable to configure security patch repositories; check log file for errors." + spUtils.RESETCOLORS
		exit(1)

        if updateZyppConf(zyppConfUpdateLogFile):
                logger.info("Successfully updated /etc/zypp/zypp.conf.")
        else:
                print spUtils.RED + "Unable to update /etc/zypp/zypp.conf; check log files for errors." + spUtils.RESETCOLORS
		exit(1)
#End init(patchDirectoryList):

#####################################################################################################
# Main program starts here.
#####################################################################################################

logger = logging.getLogger("securityPatchLogger")

def main():
	patchDirectoryList = ['kernelSecurityRPMs', 'OSSecurityRPMs']
	init(patchDirectoryList[:])
	
	

main()

#logger.info("Phase 1: Initializing system update.")

#Set traps so that the software and driver update is not interrupted by the user without first giving them a chance to continue.
#signal.signal(signal.SIGINT, signal_handler)
#signal.signal(signal.SIGQUIT, signal_handler)

