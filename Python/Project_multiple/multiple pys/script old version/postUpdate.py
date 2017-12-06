#!/usr/bin/python

from spUtils import (RED, GREEN, RESETCOLORS, firmware_signal_handler, TimeFeedbackThread)
import subprocess
import logging
import os
import shutil
import re
import datetime
import time
import optparse
import signal
import sys


'''
This function is used to configure the deadman driver on Serviceguard systems.
'''
def buildDeadmanDriver():
	
	sgDriverDir = '/opt/cmcluster/drivers'
	logger = logging.getLogger("patchLogger")

	logger.info("Rebuilding and installing the deadman driver for the new kernel.")

	#Save the current working directory, so that we can return to it after building the driver.
	cwd = os.getcwd()

	try:
		os.chdir(sgDriverDir)
	except OSError as err:
                        logger.error("Could not change into the deadman drivers directory (" + sgDriverDir + ").\n" + str(err))
                        print RED + "Could not change into the deadman drivers directory; check the log file for errors; the deadman driver will have to be manually built/installed." + RESETCOLORS
			return 'Failure'

	driverBuildCommandsList = ['make modules', 'make modules_install', 'depmod -a']

	timeFeedbackThread = TimeFeedbackThread("Rebuilding and installing the deadman driver")
	timeFeedbackThread.start()

	for command in driverBuildCommandsList:
		buildCommand = command
		result = subprocess.Popen(buildCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used in building and installing the deadman driver was: " + out.strip())

		if result.returncode != 0:
			timeFeedbackThread.stopTimer()
                        timeFeedbackThread.join()
                        logger.error("Failed to build and install the deadman driver.\n" + err)
                        print RED + "Failed to build and install the deadman driver; check the log file for errors; the deadman driver will have to be manually built/installed." + RESETCOLORS
			return 'Failure'

	timeFeedbackThread.stopTimer()
	timeFeedbackThread.join()

	try:
		os.chdir(cwd)
	except:
		pass

	logger.info("Done rebuilding and installing the deadman driver for the new kernel.")

	return 'Success'

#End buildDeadmanDriver():


'''
This function is for Scale-up systems with Fusion-IO cards and will 
install current firmware if necessary and update the driver for the 
new kernel.
'''
def updateFusionIO(patchResourceDict, **kwargs):

	firmwareUpdateRequired = kwargs['firmwareUpdateRequired']

	logger = logging.getLogger("patchLogger")

	if firmwareUpdateRequired == 'yes':
		logger.info("Updating the FusionIO firmware and software.")
		busList = (kwargs['busList']).split()
	else:
		logger.info("Updating the FusionIO software.")

	try:
		patchBaseDir = (re.sub('\s+', '', patchResourceDict['patchBaseDir'])).rstrip('/')
		fusionIOSubDir = re.sub('\s+', '', patchResourceDict['fusionIOSubDir'])

		fusionPatchDir = patchBaseDir + '/' + fusionIOSubDir
		fusionSourceDir = fusionPatchDir + '/src/'

		fusionIODriverSrcRPM = re.sub('\s+', '', patchResourceDict['fusionIODriverSrcRPM'])
	except KeyError as err:
		logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
		print RED + "A resource key was not present in the resource file; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
		return 'Failure'

	#Get the currently used kernel and processor type, which is used as part of the driver RPM name.
        command = 'uname -r'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the currently used kernel was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to get the system's current kernel information.\n" + err)
                print RED + "Unable to get the system's current kernel information; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
                return
        else:
                kernel = out.strip()

        command = 'uname -p'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the system's processor type was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to get the system's processor type.\n" + err)
                print RED + "Unable to get the system's processor type; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
		return 'Failure'
        else:
                processorType = out.strip()

	'''
	This strips off iomemory from RPM name, since it will not be needed in the regex match.
	Additionally, the source RPM is renamed to the driver RPM's name, which includes the current 
	kernel and processor type in its name.
	'''
	fusionIODriverRPM = (fusionIODriverSrcRPM.replace('iomemory-vsl', '-vsl-' + kernel)).replace('src', processorType)

	#Update the FusionIO firmware if it was determined that it is out of date.
	if firmwareUpdateRequired == 'yes':

		#Set traps so that the firmware update is not interrupted by the user.
		original_sigint_handler = signal.getsignal(signal.SIGINT)
		original_sigquit_handler = signal.getsignal(signal.SIGQUIT)
		signal.signal(signal.SIGINT, firmware_signal_handler)
		signal.signal(signal.SIGQUIT, firmware_signal_handler)

                for bus in busList:
			time.sleep(2)
                        timeFeedbackThread = TimeFeedbackThread("Updating ioDIMM in slot", bus)
                        timeFeedbackThread.start()

                        command = "fio-update-iodrive -y -f -s " + bus + ' ' + fusionPatchDir + '/' + "*.fff"
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to update the FusionIO firmware was: " + out.strip())

			timeFeedbackThread.stopTimer()
                        timeFeedbackThread.join()

			if result.returncode != 0:
				logger.error("Failed to upgrade the FusionIO firmware:\n" + err)
				print RED + "Failed to upgrade the FusionIO firmware; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
				signal.signal(signal.SIGINT, original_sigint_handler)
                		signal.signal(signal.SIGQUIT, original_sigquit_handler)
				return 'Failure'

		#Restore the signals back to their defaults.
		signal.signal(signal.SIGINT, original_sigint_handler)
                signal.signal(signal.SIGQUIT, original_sigquit_handler)

		#Remove the fio-util package before updating the software, since it is no longer needed for any firmware updates.
		command = "rpm -e fio-util"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to remove the fio-util package before updating the FusionIO software was: " + out.strip())

		if result.returncode != 0:
			logger.error("Failed to remove the fio-util package:\n" + err)
			print RED + "Failed to remove the fio-util package; check the log file for errors; the FusionIO software/driver will have to be updated manually." + RESETCOLORS
			return 'Failure'

	#Build the driver for the new kernel.
	timeFeedbackThread = TimeFeedbackThread("Updating the FusionIO driver and software")
	timeFeedbackThread.start()

	command = "rpmbuild --rebuild " + fusionSourceDir + "*.rpm"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to build the FusionIO driver was: " + out.strip())

	if result.returncode != 0:
		timeFeedbackThread.stopTimer()
		timeFeedbackThread.join()
		logger.error("Failed to build the FusionIO driver:\n" + err)
		print RED + "Failed to build the FusionIO driver; check the log file for errors; the FusionIO software/driver will have to be updated manually." + RESETCOLORS
		return 'Failure'

	out = out.strip()

	#Compile the regex that will be used to get the driver RPM location.
	fusionIODriverPattern = re.compile('.*Wrote:\s+((/[0-9,a-z,A-Z,_]+)+' + fusionIODriverRPM +')', re.DOTALL)

	logger.debug("The regex used to get the FusionIO driver RPM location was: " + fusionIODriverPattern.pattern)

	driverRPM = re.match(fusionIODriverPattern, out).group(1)

	logger.debug("The FuionIO driver was determined to be: " + driverRPM)

	#Now copy the new driver RPM to the FusionIO patch directory so that it gets installed with the rest of the RPMs.
	try:
		shutil.copy2(driverRPM, fusionPatchDir)
	except IOError as err:
		timeFeedbackThread.stopTimer()
		timeFeedbackThread.join()
		logger.error("Unable to retrieve the driver RPM.\n" + err)
                print RED + "Unable to retrieve the driver RPM; check log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
		return 'Failure'

	#Update the FusionIO software.
	command = "rpm -ivh " + fusionPatchDir + '/' + "*.rpm"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to update the FusionIO software was: " + out.strip())

	if result.returncode != 0:
		timeFeedbackThread.stopTimer()
		timeFeedbackThread.join()
		logger.error("Failed to update the FusionIO software:\n" + err)
		print RED + "Failed to update the FusionIO software; check the log file for errors; the FusionIO software/driver will have to be updated manually." + RESETCOLORS
		return 'Failure'

	if firmwareUpdateRequired == 'yes':
		logger.info("Done Updating the FusionIO firmware and software.")
	else:
		logger.info("Done Updating the FusionIO software.")

	timeFeedbackThread.stopTimer()
	timeFeedbackThread.join()

	return 'Success'

#End updateFusionIO():


'''
This function cleans up as a final step of the system update.
'''
def cleanup():

	pass

#End cleanup():


#This section is for running the module standalone for debugging purposes.
if __name__ == '__main__':

	parser = optparse.OptionParser()
	parser.add_option('-d', action='store_true', default=False, help='This option is for testing the deadman driver.')
        parser.add_option('-f', action='store_true', default=False, help='This option is for testing the FusionIO upgrade.')

	(options, args) = parser.parse_args()

	patchResourceFile = '/hp/support/patches/resourceFiles/patchResourceFile'

	#Setup logging.
	logger = logging.getLogger()
	logFile = 'postUpdate.log'

        try:
                open(logFile, 'w').close()
        except IOError:
                print RED + "Unable to access " + logFile + " for writing." + RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.INFO)
	handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	if options.d:
		if buildDeadmanDriver():
			print GREEN + "Successfully built and installed the deadman driver." + RESETCOLORS
		else:
			print RED + "Failed to build and install the deadman driver; check the log file for errors." + RESETCOLORS
	elif options.f:
		if updateFusionIO():
			print GREEN + "Successfully upgraded the FusionIO." + RESETCOLORS
		else:
			print RED + "Failed to upgrade the FusionIO; check the log file for errors." + RESETCOLORS
