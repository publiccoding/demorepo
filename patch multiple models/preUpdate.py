#!/usr/bin/python

from spUtils import RED, RESETCOLORS
import subprocess
import logging
import os
import re
import datetime


'''
This function is used to remove FusionIO packages on Scale-up systems with
FusionIO cards before the FusionIO cards are updated.
However, the 'fio-util' package will have to be removed after
the firmware is updated if necessary, since it is needed for the update.
'''
def removeFusionIOPackages(patchResourceDict, loggerName):

	logger = logging.getLogger(loggerName)

	logger.info("Removing FusionIO packages.")

	#Get the list of FusionIO firmware versions and revisions that are supported for automatic upgrades and log file names/locations.
	try:
		fusionIOFirmwareList = patchResourceDict['fusionIOFirmwareVersionList']

		currentFusionIOFirmwareVersion = patchResourceDict['currentFusionIOFirmwareVersion']

                logBaseDir = (re.sub('\s+', '', patchResourceDict['logBaseDir'])).rstrip('/')

                postUpdateResumeLog = re.sub('\s+', '', patchResourceDict['postUpdateResumeLog'])
                postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog

                fioStatusLog = re.sub('\s+', '', patchResourceDict['fioStatusLog'])
                fioStatusLog = logBaseDir + '/' + fioStatusLog
	except KeyError as err:
		logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
		print RED + "The resource key for the FusionIO firmware list was not present in the resource file; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	#Create fio-status log file.
	try:
		open(fioStatusLog, 'w').close()
        except IOError as err:
                logger.error("Unable to access the FusionIO status log (" + fioStatusLog + ") for writing.\n" + str(err))
                print RED + "Unable to access the FusionIO status log for writing; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

	command = "fio-status > " + fioStatusLog
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get FusionIO status was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to get the system's FusionIO firmware version.\n" + strerr)
                print RED + "Unable to get the system's FusionIO firmware version; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

	busList = []
	firmwareUpdateRequired = 'no'

	'''
	Check the currently installed firmware revision.  If the revision installed is supported for an automatic upgrade then document whether or 
	not it needs to be upgraded.  Also, save the ioDIMM bus list as it will be needed for the upgrade.
	'''
	try:
		with open(fioStatusLog) as f:
			count = 0
			ioDIMMStatusDict = {}

			for line in f:
				line = line.strip()

				if "Firmware" in line or re.search('PCI:[0-9,a-f]{2}:[0-9]{2}\.[0-9]{1}', line):
					if "Firmware" in line:
						ioDIMMStatusDict['Firmware'] = line
					else:
						ioDIMMStatusDict['bus'] = line
					count += 1

				if count == 2:
					fwInstalledVersion = re.match("Firmware\s+(v.*),\s+.*[0-9]{6}", ioDIMMStatusDict['Firmware']).group(1)

					logger.debug("The installed FusionIO firmware version was determined to be: " + fwInstalledVersion)

					#Check to ensure that the current FusionIO firmware is at a supported level for an automated upgrade.
					if fwInstalledVersion not in fusionIOFirmwareList:
					       	logger.error("Unable to proceed until the FusionIO firmware is updated, since it is at an unsupported version (" + fwInstalledVersion + ").")
						print RED + "Unable to proceed until the FusionIO firmware is updated, since it is at an unsupported version; check the log file for errors; exiting program execution." + RESETCOLORS
						exit(1)
					elif fwInstalledVersion != currentFusionIOFirmwareVersion:
						firmwareUpdateRequired = 'yes'
						busList.append(re.match('.*([0-9,a-f]{2}:[0-9]{2}\.[0-9]{1})', ioDIMMStatusDict['bus']).group(1))

					ioDIMMStatusDict.clear()
					count = 0
	except IOError as err:
		logger.error("Unable to get the FusionIO firmware version from the patch resource file.\n" + str(err))
		print RED + "Unable to get the FusionIO firmware version from the patch resource file; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

        try:
                f = open(postUpdateResumeLog, 'a')

		f.write("firmwareUpdateRequired = " + firmwareUpdateRequired + "\n")

		if firmwareUpdateRequired == 'yes':
			f.write("busList = '" + ' '.join(busList) + "'" + "\n")

		f.close()
        except IOError as err:
                logger.error("Unable to access the post update resume log (" + postUpdateResumeLog + ") for writing.\n" + str(err))
                print RED + "Unable to access the post update resume log for writing; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

	fusionIOPackageList = [
			'^fio*',
			'^hp-io-accel-msrv*',
			'^iomemory-vsl*',
			'^libfio*',
			'^libvsl*'
		       ]

	packageRemovalList = []

	#Before trying to remove a package we need to see if it is present.
	for package in fusionIOPackageList:
		command = "rpm -qa " + package
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        	out, err = result.communicate()
        	var = (out.strip()).split()

		logger.debug("The output of the command (" + command + ") used to get the currently installed FusionIO software was: " + out.strip())

        	if len(var) > 0:
                	packageRemovalList.extend(var)

	#We don't want to remove fio-util if a firmware update is needed, since it will be needed to perform the update.
	if firmwareUpdateRequired == 'yes':
		for package in packageRemovalList:
			if 'fio-util' in package:
				packageRemovalList.remove(package)
	
	#Now remove any of the packages that were present.
	packages = " ".join(packageRemovalList)

	if len(packages) > 0:
		command = "rpm -e " + packages

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to remove the currently installed FusionIO software was: " + out.strip())

		if result.returncode != 0:
				logger.error("Problems were encountered while trying to remove the FusionIO packages.")
				logger.error("The following errors were encountered: " + err)
				print RED + "Problems were encountered while trying to remove the FusionIO packages; check the log file for errors; exiting program execution." + RESETCOLORS
				exit(1)
	return True
#End removeFusionIOPackages(patchResourcDict, loggerName):


'''
This function is used to check what OS is installed and that it is a supported OS
at the correct service pack level.  Currently Red Hat is not supported.
The osDistLevel is returned.
'''
def checkOSVersion(patchResourceDict, loggerName):

	logger = logging.getLogger(loggerName)

	logger.info("Checking and getting the OS distribution information.")

        command = "cat /proc/version"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the OS distribution information was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to get system OS type.\n" + err)
                print RED + "Unable to get system OS type; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

        if 'SUSE' in out:
                '''
                Check to make sure that the OS is SLES4SAP and that it is a supported service pack level.
                '''
                try:
                        with open('/etc/products.d/SUSE_SLES_SAP.prod') as f:
                                for line in f:
                                        if "SUSE_SLES_SAP-release" in line:
                                                version = re.match("^.*version=\"([0-9]{2}.[0-9]{1}).*", line).group(1)

                                                if version in patchResourceDict:
                                                        osDistLevel = (patchResourceDict[version]).lstrip()
                                                else:
                                                        logger.error("The SLES Service Pack level (" + version + ") installed is not supported.")
                                                        print RED + "The SLES Service Pack level installed is not supported; check the log file for additional information; exiting program execution." + RESETCOLORS
							exit(1)
                                                break
                except IOError as err:
                        logger.error("Unable to determine the SLES OS type.\n" + str(err))
                        print RED + "Unable to determine the SLES OS type; check the log file for errors; exiting program execution." + RESETCOLORS
                        exit(1)
        elif 'Red Hat' in out:
                logger.error("The compute node is installed with Red Hat, which is not yet supported.")
                print RED + "The compute node is installed with Red Hat, which is not yet supported; exiting program execution." + RESETCOLORS
		exit(1)
        else:
                logger.error("The compute node is installed with an unsupported OS.")
                print RED + "The compute node is installed with an unsupported OS; exiting program execution." + RESETCOLORS
		exit(1)

	logger.info("Done checking and getting the OS distribution information.")

	logger.debug("The OS distribution level was determined to be: " + osDistLevel)

	return osDistLevel

#End checkOSVersion(patchResourceDict, loggerName):


'''
This function is used to check the available disk space of the root file system.
There needs to be at least 2GB free.
'''
def checkDiskSpace(loggerName):

	logger = logging.getLogger(loggerName)

	logger.info("Checking the available disk space of the root file system.")

        command = "df /"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the root file system's disk usage was: " + out.strip())

        if result.returncode != 0:
                logger.error("Unable to check the available disk space of the root file system.\n" + err)
                print RED + "Unable to check the available disk space of the root file system; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

	out = out.strip()

	tmpVar = re.match('(.*\s+){3}([0-9]+)\s+', out).group(2)

	availableDiskSpace = round(float(tmpVar)/float(1024*1024), 2)

	logger.debug("The root file system's available disk space was determined to be: " + str(availableDiskSpace) + 'GB')

	if not availableDiskSpace >= 2:
                logger.error("There is not enough disk space (" + availableDiskSpace + "GB) on the root file system. There needs to be at least 2GB of free space on the root file system.\n")
                print RED + "There is not enough disk space on the root file system; check the log file for errors; exiting program execution." + RESETCOLORS
                exit(1)

	logger.info("Done checking the available disk space of the root file system.")

#End checkDiskSpace(loggerName):


'''
This function sets the patch directories and the kernel patch directory based on whether or not 
the system is a Superdome system.  It returns a list of the directories once it confirms that the directories exist. 
'''
def setPatchDirectories(patchResourceDict, loggerName):
		
	logger = logging.getLogger(loggerName)

	logger.info("Setting and getting the patch directories.")

	#This holds the list of patch directories that will be used for the update.
	patchDirList = []

	options = patchResourceDict['options']

	#Set the kernel directory for options a or k.
        if options.a or options.k:
		command = "dmidecode -s system-product-name"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the system's product type was: " + out.strip())

		if result.returncode != 0:
			logger.error("Unable to get the system product type.\n" + err)
			print RED + "Unable to get the system product type; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)

		if 'Superdome' in out:
			kernelDirKey = 'cs900KernelSubDir'
		else:
			kernelDirKey = 'kernelSubDir'

		try:
			patchBaseDir = (re.sub('\s+', '', patchResourceDict['patchBaseDir'])).rstrip('/')
			kernelDir = re.sub('\s+', '', patchResourceDict[kernelDirKey])
			osDistLevel = re.sub('\s+', '', patchResourceDict['osDistLevel'])
			kernelDir = patchBaseDir + '/' + osDistLevel + '/' + kernelDir
		except KeyError as err:
			logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
			print RED + "A resource key was not present in the resource file; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)

	#Set the OS directory for options a or o.
        if options.a or options.o:
		try:
			patchBaseDir = (re.sub('\s+', '', patchResourceDict['patchBaseDir'])).rstrip('/')
			osDir = re.sub('\s+', '', patchResourceDict['osSubDir'])
			osDistLevel = re.sub('\s+', '', patchResourceDict['osDistLevel'])
			osDir = patchBaseDir + '/' + osDistLevel + '/' + osDir
		except KeyError as err:
			logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
			print RED + "A resource key was not present in the resource file; check the log file for errors; exiting program execution." + RESETCOLORS
			exit(1)
	
        #Verify that the patch directories exist.
        if options.a:
                if not (os.path.exists(kernelDir) and os.path.exists(osDir)):
                        logger.error("Option -a was selected, however, both of the OS and kernel patch directories (" + kernelDir + ", " + osDir + ") are not present.")
                        print RED + "Option -a was selected, however, both of the OS and kernel security patch directories are not present; check the log file for further information; exiting program execution.\n" + RESETCOLORS
                        exit(1)
		else:
			patchDirList.append(kernelDir)
			patchDirList.append(osDir)
			
        elif options.k:
                if not os.path.exists(kernelDir):
                        logger.error("Option -k was selected, however, the kernel patch directory (" + kernelDir + ") is not present.")
                        print RED + "Option -k was selected, however, the kernel patch directory is not present; check the log file for further information; exiting program execution.\n" + RESETCOLORS
                        exit(1)
		else:
			patchDirList.append(kernelDir)
        else:
                if not os.path.exists(osDir):
                        logger.error("Option -o was selected, however, the OS patch directory (" + osDir + ") is not present.")
                        print RED + "Option -o was selected, however, the OS patch directory is not present; check the log file for further information; exiting program execution.\n" + RESETCOLORS
                        exit(1)
		else:
			patchDirList.append(osDir)
	
	logger.info("Done setting and getting the patch directories.")

	logger.debug("The patch directory list was determined to be: " + str(patchDirList))

	return patchDirList

#End setPatchDirectories(patchResourceDict, loggerName):


'''
This function checks to see whether or not the system is a Gen 1.0 Scale-up system with FusionIO cards and/or a system
with Serviceguard installed. It returns whether or not a post update is required.
'''
def checkSystemConfiguration(patchResourceDict, loggerName):
		
	logger = logging.getLogger(loggerName)

	logger.info("Checking the system's configuration.")

	postUpdateRequired = ''

	#Get the post update resume log, which contains information for the post update tasks.
	try:
		logBaseDir = (re.sub('\s+', '', patchResourceDict['logBaseDir'])).rstrip('/')
		postUpdateResumeLog = re.sub('\s+', '', patchResourceDict['postUpdateResumeLog'])
		postUpdateResumeLog = logBaseDir + '/' + postUpdateResumeLog
	except KeyError as err:
		logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
		print RED + "The resource key for the post update resume log was not present in the resource file; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	#Serviceguard should only be installed on dual purpose or nfs servers.
        command = "rpm -q serviceguard"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to determine if Serviceguard was installed was: " + out.strip())

	try:
		f = open(postUpdateResumeLog, 'a')

        	if result.returncode == 0:
			f.write("isServiceguardSystem = yes\n")
			postUpdateRequired = 'yes'
		else:
			f.write("isServiceguardSystem = no\n")

		f.close()
	except IOError as err:
		logger.error("Unable to access the post update resume log.\n" + str(err))
		print RED + "Unable to access the post update resume log; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)
	
	#FusionIO should only be installed on Gen 1.0 Scale-up systems.
	try:
		f = open(postUpdateResumeLog, 'a')

		fioStatus = '/usr/bin/fio-status'

		if os.path.exists(fioStatus):
			command = fioStatus + ' -c'
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to determine then number of FusionIO cards was: " + out.strip())

			if result.returncode == 0:
				if out.strip() > 0:
					f.write("isFusionIOSystem = yes\n")
					postUpdateRequired = 'yes'
					removeFusionIOPackages(patchResourceDict.copy(), loggerName)
				else:
					logger.info("fio-status was present, but it appears the system does not have any FusionIO cards.\n")
			else:
				logger.error("Unable to determine the number of FusionIO cards installed.\n" + str(err))
				print RED + "Unable to determine the number of FusionIO cards installed; check the log file for errors; exiting program execution." + RESETCOLORS
				exit(1)
		else:
			f.write("isFusionIOSystem = no\n")
	except IOError as err:
		logger.error("Unable to access the post update resume log.\n" + str(err))
		print RED + "Unable to access the post update resume log; check the log file for errors; exiting program execution." + RESETCOLORS
		exit(1)

	f.close()

	logger.info("Done checking the system's configuration.")

	return postUpdateRequired

#End checkSystemConfiguration(postUpdateResumeLog):


'''
#This section is for running the module standalone for debugging purposes.  Uncomment to use.
if __name__ == '__main__':

	patchResourceFile = '/hp/support/patches/resourceFiles/patchResourceFile'

	#Setup logging.
	loggerName = 'testLogger'
	logger = logging.getLogger(loggerName)
	logFile = 'preUpdate.log'

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
	
	#Save the options for later use.
        patchResourceDict['options'] = options

        #Get patch resource file data and save it to a dictionary (hash).
        try:
                with open(applicationResourceFile) as f:
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
                                        patchResourceDict[key] = val.lstrip()
        except IOError as err:
                print RED + "Unable to access the application's resource file " + applicationResourceFile + ".\n" + str(err) + "\n" + RESETCOLORS
                exit(1)

	#Uncomment each function to test.  Also, some of the funtions have a return value; thus this needs to be taken into account when testing.
	#removeFusionIOPackages(patchResourceDict.copy(), loggerName)
	#checkOSVersion(patchResourceDict.copy(), loggerName):
	#checkDiskSpace(loggerName):
	#setPatchDirectories(patchResourceDict.copy(), loggerName):
	#checkSystemConfiguration(patchResourceDict.copy(), loggerName):
'''
