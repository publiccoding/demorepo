#!/usr/bin/python

from spUtils import RED, RESETCOLORS
import subprocess
import logging
import datetime
import shutil


'''
This function is used to update /etc/zypp/zypp.conf so that two kernels will be maintained. The 
new kernel and the previous kernel. Thus, there is a fallback kernel in case the new kernel
results in unforeseen issues.
'''
def updateZyppConf(loggerName):

	logger = logging.getLogger(loggerName)

	zyppConfigurationFile = '/etc/zypp/zypp.conf'

	logger.info("Updating the system's zypper configuration file.")

        #Use date to create a time specific backup of the bootloader configuration file.
        dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

        #Make a backup of the current zypp.conf configuration.
        try:
                shutil.copy2(zyppConfigurationFile, zyppConfigurationFile + '.' + dateTimestamp)
        except IOError as err:
                logger.error("Unable to make a backup of the system's zypper configuration file.\n" + str(err))
                print RED + "Unable to make a backup of the system's zypper configuration file; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	#This will update the multiversion resource so that multiple kernels are allowed.
	command = 'egrep "^\s*multiversion\s*=\s*" ' + zyppConfigurationFile
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the multiversion resource from " + zyppConfigurationFile + " was: " + out.strip())

	if result.returncode == 0:
		command = "sed -i '0,/^\s*multiversion\s*=\s*.*$/s//multiversion = provides:multiversion(kernel)/' " + zyppConfigurationFile
	else:
		command = "sed -i '0,/^\s*#\+\s*multiversion\s*=\s*.*$/s//multiversion = provides:multiversion(kernel)/' " + zyppConfigurationFile

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to update the multiversion resource was: " + out.strip())

	if result.returncode != 0:
		logger.error("Unable to update the system's zypper configuration file " + zyppConfigurationFile + ".\n" + err)
		print RED + "Unable to the system's zypper configuration file ; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)
	
	#This will update the multiversion.kernels resource so that the two most recent kernels kept.
	command = 'egrep "^\s*multiversion.kernels\s*=\s*" ' + zyppConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the multiversion.kernels resource from " + zyppConfigurationFile + " was: " + out.strip())

        if result.returncode == 0:
                command = "sed -i '0,/^\s*multiversion.kernels\s*=\s*.*$/s//multiversion.kernels = latest,latest-1,running/' " + zyppConfigurationFile
        else:
                command = "sed -i '0,/^\s*#\+\s*multiversion.kernels\s*=\s*.*$/s//multiversion.kernels = latest,latest-1,running/' " + zyppConfigurationFile

        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to update the multiversion.kernels resource was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to update the system's zypper configuration file " + zyppConfigurationFile + ".\n" + err)
                print RED + "Unable to the system's zypper configuration file ; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

	logger.info("Done updating the system's zypper configuration file.")

#End def updateZyppConf(loggerName):


'''
#This section is for running the module standalone for debugging purposes. Uncomment to use.
if __name__ == '__main__':

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = '/tmp/updateZyppConf.log'
	zyppConfScriptLogFile = '/tmp/updateZyppConfScript.log'
	zyppConf = '/etc/zypp/zypp.conf'

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

	updateZyppConf(loggerName)
'''
