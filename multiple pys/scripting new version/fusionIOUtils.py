import subprocess
import logging
import re


'''
This function is used to remove FusionIO packages before they are updated.
'''
def removeFusionIOPackages(packageList, type, loggerName):
	logger = logging.getLogger(loggerName)

	removalStatus = False

	logger.info("Removing FusionIO " + type + " packages.")

	packageList = re.sub('\s+', '', packageList)

	fusionIOPackageList = packageList.split(',')

	packageRemovalList = []

	#Before trying to remove a package we need to see if it is present.
	for package in fusionIOPackageList:
		command = "rpm -q " + package
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        	out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the currently installed FusionIO " + type + " package was: " + out.strip())

	        if result.returncode != 0:
			if err != '':
				if "is not installed" in err:
					self.logger.info("The " + type + " package '" + package + "' was not installed.")
					continue
				else:
					self.logger.error("Failed to verify if the " + type + " package '" + package + "' was installed.\n" + err)
					continue
			else:
				self.logger.error("Failed to verify if the " + type + " package '" + package + "' was installed.\n" + out)
				continue
		else:
                	packageRemovalList.extend(out.splitlines())

	#Now remove any of the packages that were present.
	packages = " ".join(packageRemovalList)

	if len(packages) > 0:
		command = "rpm -e " + packages

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to remove the currently installed FusionIO " + type + " package(s) was: " + out.strip())

		if result.returncode != 0:
				logger.error("Problems were encountered while trying to remove the FusionIO " + type + " packages.\n" + err)
		else:
			removalStatus = True

	logger.info("Done removing FusionIO " + type + " packages.")

	return removalStatus

#End removeFusionIOPackages(packageList, type, loggerName):


'''
This function is used to check if the FusionIO firmware is at a supported level for 
an automatic upgrade.
'''
def checkFusionIOFirmwareUpgradeSupport(fusionIOFirmwareVersionList, loggerName):
        logger = logging.getLogger(loggerName)

	upgradeStatus = True

        logger.info("Checking to see if the FusionIO firmware is at a supported version for an automatic upgrade.")

	command = "fio-status"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the FusionIO firmware information was: " + out.strip())

	if result.returncode != 0:
		logger.error("Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.\n" + err)
		upgradeStatus = False
	else:
		fioStatusList = out.splitlines()

		for line in fioStatusList:
			line = line.strip()

			if "Firmware" in line:
				firmwareVersion = re.match("Firmware\s+(v.*),", line).group(1)

				logger.debug("The ioDIMM firmware version was determined to be: " + firmwareVersion  + ".")

				if firmwareVersion not in fusionIOFirmwareVersionList:
					logger.error("The fusionIO firmware is not at a supported version for an automatic upgrade.")
					upgradeStatus = False
					break
			else:
				continue

        logger.info("Done checking to see if the FusionIO firmware is at a supported level for an automatic upgrade.")

	return upgradeStatus

#End checkFusionIOFirmwareUpgradeSupport(fusionIOFirmwareVersionList, loggerName):
