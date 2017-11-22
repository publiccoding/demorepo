#!/usr/bin/python

import subprocess
import re
import os
import logging
import shutil
import time
import traceback
import datetime
from modules.cursesThread import CursesThread


RED = '\033[31m'
PURPLE = '\033[35m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BOLD = '\033[1m'
RESETCOLORS = '\033[0m'


'''
The purpose of this script is restore OS configuration after a SLES 12.1
upgrade is performed.

Author Bill Neumann
'''

def checkPreupgradeArchive(programParentDir, restorationArchiveErrorFile, cursesThread):
	restorationArchiveFile = ''

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Checking the preupgrade restoration archive to make sure it is not corrupt.')

	archiveFileRegex = re.compile('.*Restoration_Backup_For_SLES_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')

	archiveImageDir = programParentDir + '/archiveImages'

	#Check for preupgrade archive image.
        command = 'ls ' + archiveImageDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Unable to get a listing of the files in \'' + archiveImageDir + '\'.\n' + err + '\n' + out)
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
		displayErrorMessage('Unable to get a listing of the files in \'' + archiveImageDir + '\'; fix the problem and try again.', cursesThread)

	fileList = out.splitlines()

	archiveFound = False

	for file in fileList:
		if re.match(archiveFileRegex, file):
			md5sumFile = re.sub('tar.gz', 'md5sum', file)
			restorationArchiveFile = archiveImageDir + '/' + file
			archiveMd5sumFile = archiveImageDir + '/' + md5sumFile
			archiveFound = True
			break

	if not archiveFound:
                logger.error('The upgrade restoration archive \'' + archiveImageDir + '/' + archiveFileRegex.pattern + '\' could not be found.')
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
		displayErrorMessage('The upgrade restoration archive \'' + archiveImageDir + '/' + archiveFileRegex.pattern + '\' could not be found; fix the problem and try again.', cursesThread)

	if not os.path.isfile(archiveMd5sumFile):
                logger.error('The upgrade restoration archive\'s md5sum file \'' + archiveMd5sumFile + '\' is missing.')
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
                displayErrorMessage('The upgrade restoration archive\'s md5sum file \'' + archiveMd5sumFile + '\' is missing; fix the problem and try again.', cursesThread)

        command = 'md5sum ' + restorationArchiveFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Unable to determine the md5sum of the restoration upgrade archive \'' + restorationArchiveFile + '\'.\n' + err + '\n' + out)
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
                displayErrorMessage('Unable to determine the md5sum of the restoration upgrade archive \'' + restorationArchiveFile + '\'; fix the problem and try again.', cursesThread)

	try:
        	upgradeArchiveMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)
	except AttributeError as err:
		logger.error('There was a match error when trying to match against ' + out + '.\n' + str(err))
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
		displayErrorMessage('There was a match error when matching against \'' + out + '\'; fix the problem and try again.', cursesThread)

        try:
                with open(archiveMd5sumFile) as f:
                        for line in f:
                                line = line.strip()
                                if file in line:
                                        archiveMd5sum = re.match('([0-9,a-f]*)\s+', line).group(1)
        except IOError as err:
                logger.error('Unable to get the md5sum of the upgrade archive from \'' + archiveMd5sumFile + '\'.\n' + str(err))
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
                displayErrorMessage('Unable to get the md5sum of the upgrade archive from \'' + archiveMd5sumFile + '\'; fix the problem and try again.', cursesThread)
	except AttributeError as err:
		logger.error('There was a match error when trying to match against \'' + line + '\'.\n' + str(err))
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
		displayErrorMessage('There was a match error when matching against \'' + line + '\'; fix the problem and try again.', cursesThread)

        if upgradeArchiveMd5sum != archiveMd5sum:
                logger.error('The upgrade archive \'' + restorationArchiveFile + '\' is corrupt; its md5sum does not match its md5sum in \'' + archiveMd5sumFile + '\'.')
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
                displayErrorMessage('The upgrade archive \'' + restorationArchiveFile + '\' is corrupt; fix the problem and try again.', cursesThread)

	logger.info('Done checking the preupgrade restoration archive to make sure it is not corrupt.')

	return restorationArchiveFile

#End checkPreupgradeArchive(programParentDir, restorationArchiveErrorFile, cursesThread):


'''
This function extracts the preupgrade archive file.
'''
def extractPreupgradeArchive(preUpgradeFile, restorationArchiveErrorFile, cursesThread):
	restorationArchiveExtracted = True

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Extracting the restoration archive image.')

        command = 'tar -zxf ' + preUpgradeFile + ' -C /'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.info('The command used to extract the restoration archive was: \'' + command + '\'.')

        if result.returncode != 0:
                logger.error('There was a problem extracting the preupgrade file ' + preUpgradeFile + '.\n' + err + '\n' + out)
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
                displayErrorMessage('There was a problem extracting the preupgrade file \'' + preUpgradeFile + '\'; fix the problem and try again.', cursesThread)
		restorationArchiveExtracted = False

	logger.info('Done extracting the restoration archive image.')

	return restorationArchiveExtracted

#End extractPreupgradeArchive(preUpgradeFile, restorationArchiveErrorFile, cursesThread):


'''
This function updates the restoration archive error file, which is used to keep track of the number of attempts.
'''
def updateRestorationArchiveErrorFile(restorationArchiveErrorFile):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Updating the restoration archive error file with an archive failure attempt.')

	try:
		f = open(restorationArchiveErrorFile, 'a')

		if os.stat(restorationArchiveErrorFile).st_size == 0:
			f.write('First Attempt Failed\n')
		elif os.stat(restorationArchiveErrorFile).st_size  < 25:
			f.write('Second Attempt Failed\n')
		elif os.stat(restorationArchiveErrorFile).st_size  < 45:
			f.write('Third Attempt Failed\n')
	except IOError as err:
		logger.error('Could not write to the restoration archive error file ' + restorationArchiveErrorFile + '.\n' + str(err))
                displayErrorMessage('Could not write to the restoration archive error file \'' + restorationArchiveErrorFile + '\'; fix the problem and try again.', cursesThread)

	f.close()

	logger.info('Done updating the restoration archive error file with an archive failure attempt.')

#End updateRestorationArchiveErrorFile(restorationArchiveErrorFile):


'''
This function upgrades the server's BIOS settings using a predetermined conrep file.
'''
def updateBIOS(programParentDir, cursesThread):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Updating the server\'s BIOS.')
	cursesThread.insertMessage(['informative', 'Updating the server\'s BIOS.'])
	cursesThread.insertMessage(['informative', ''])

	command = 'conrep -l -f ' + programParentDir + '/conrepFile/conrep.dat'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.info('The command used to update the server\'s BIOS was: \'' + command + '\'.')

	if result.returncode != 0:
		logger.error('An error was encountered when updating the server\'s BIOS.\n' + err + '\n' + out)
		errorMessage = 'An error was encountered when updating the server\'s BIOS.'
		return errorMessage
	
	logger.info('Done updating the server\'s BIOS.')

	return errorMessage

#End updateBIOS(programParentDir, cursesThread):


'''
This function upgrades the server's OS settings according to the following SAP Note:
	- SAP Note 2205917 - SAP HANA DB Recommended OS settings for SLES 12
'''
def updateOSSettings(cursesThread):
	errorMessageList = []

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Updating the server\'s OS settings according to SAP Note 2205917.')
	cursesThread.insertMessage(['informative', 'Updating the server\'s OS settings according to SAP Note ' + sapNote + '.'])
	cursesThread.insertMessage(['informative', ''])

	#Update sap-hana.conf.
	sapHanaCfgDir = '/etc/systemd/logind.conf.d'	
	sapHanaCfgFile = sapHanaCfgDir + '/sap-hana.conf'

	if not os.path.isdir(sapHanaCfgDir):
		sapHanaCfgDirCreated = True

		try:
			os.mkdir(sapHanaCfgDir)
		except OSError as err:
			logger.error('Unable to create the login manager configuration directory \'' + sapHanaCfgDir + '\'.\n' + str(err))
			errorMessageList.append('Unable to create the login manager configuration directory \'' + sapHanaCfgDir + '\' to update sap-hana.conf.')
			sapHanaCfgDirCreated = False

		if sapHanaCfgDirCreated:	
			#The file will not exist to start with.
			if not os.path.isfile(sapHanaCfgFile):
				loginData = '[Login]\nUserTasksMax=1000000'

				try:
					f = open(sapHanaCfgFile, 'w')
					f.write(loginData)
				except IOError as err:
					logger.error('Could not write the login configuration to \'' + sapHanaCfgFile + '\'.\n' + str(err))
					errorMessageList.append('Could not write the login configuration to \'' + sapHanaCfgFile + '\'.')

				f.close()

	#Update tuned.conf with force_latency=70.
	tunedConfFile = '/usr/lib/tuned/sap-hana/tuned.conf'

	command = "sed -i 's/\[cpu]/&\\nforce_latency=70/' " + tunedConfFile
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.info('The command used to update force_latency in \'' + tunedConfFile + '\' was: ' + command + '.')

	if result.returncode != 0:
		logger.error('Could not write the force_latency resource to \'' + tunedConfFile + '\'.\n' + err + '\n' + out)
		errorMessageList.append('Could not write the force_latency resource to \'' + tunedConfFile + '\'.')

	#Update grub with proper C-States settings.
	updateMade = False

	grubCfgFile = '/etc/default/grub'

	try:
		with open(grubCfgFile) as f:
			for line in f:
				line = line.strip()

				if re.match('\s*GRUB_CMDLINE_LINUX_DEFAULT=', line) != None:
					grubDefault = line

					if 'intel_idle.max_cstate' in grubDefault:
						if re.match('.*intel_idle.max_cstate=1', grubDefault) == None:
							grubDefault = re.sub('intel_idle.max_cstate=[0-9]{1}', 'intel_idle.max_cstate=1', grubDefault)
							updateMade = True
					else:
						grubDefault = grubDefault[:-1] + ' intel_idle.max_cstate=1"'
						updateMade = True

					if 'processor.max_state' in grubDefault:
						if re.match('.*processor.max_state=1', grubDefault) == None:
							grubDefault = re.sub('processor.max_state=[0-9]{1}', 'processor.magxstate=1', grubDefault)

							if not updateMade:
								updateMade = True
					else:
						grubDefault = grubDefault[:-1] + ' processor.max_state=1"'

						if not updateMade:
							updateMade = True

					break
	except OSError as err:
		logger.error('Unable to access grub\'s default configuration file \'' + grubCfgFile + '\' to update its C-States.\n' + str(err))
		errorMessageList.append('Unable to access grub\'s default configuration file \'' + grubCfgFile + '\' to update its C-States.')

	if updateMade:
		command = "sed -i 's|^\s*GRUB_CMDLINE_LINUX_DEFAULT=.*|" + grubDefault + "|' " + grubCfgFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.info('The command used to update grub\'s default configuration file \'' + grubCfgFile + '\' C-States was: \'' + command + '\'.')

		if result.returncode != 0:
			logger.error('Could not update the C-States settings in \'' + grubCfgFile + '\'.\n' + err + '\n' + out)
			errorMessageList.append('Could not update the C-States settings in ' + grubCfgFile + '.')
		else:
			bootGrubCfgFile = '/boot/grub2/grub.cfg'

			command = 'grub2-mkconfig -o ' + bootGrubCfgFile
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.info('The command used to generate a new grub.cfg file was: \'' + command + '\'.')

			if result.returncode != 0:
				logger.error('Could not update the GRUB2 configuration with the updated C-States settings.\n' + err + '\n' + out)
				errorMessageList.append('Could not update the GRUB2 configuration with the updated C-States settings.')

	logger.info('Done updating the server\'s OS settings according to SAP Note' + sapNote + '.')

	return errorMessageList

#End updateOSSettings(cursesThread):


'''
This function installs/resplaces additional files.
'''
def installAddOnFiles(programParentDir, processor, cursesThread):
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
	logger.info('Installing/replacing the files from the add-on archive.')
	cursesThread.insertMessage(['informative', 'Installing/replacing the files from the add-on archive.'])
	cursesThread.insertMessage(['informative', ''])

	if processor == 'ivybridge':
		addOnFileArchive = programParentDir + '/addOnFileArchive/ivyBridgeAddOnFiles.tar.gz'
	else:
		addOnFileArchive = programParentDir + '/addOnFileArchive/haswellAddOnFiles.tar.gz'
	
	command = 'tar -zxf ' + addOnFileArchive + ' -C /'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('An error was encountered while installing/replacing the files from the add-on file archive.\n' + err + '\n' + out)
		errorMessage = 'An error was encountered while installing/replacing the files from the add-on file archive.'
		return errorMessage

	logger.info('Done installing/replacing the files from the add-on archive.')

	return errorMessage

#End installAddOnFiles(programParentDir, processor, cursesThread):


'''
This function checks the network configuration; specifically it checks to see that the NIC cards have not been renamed
and if so it remaps to the new names using the previosly saved MAC addresses.
'''
def checkNetworkConfiguration(programParentDir, cursesThread):
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
	logger.info('Checking the network configuration.')
	cursesThread.insertMessage(['informative', 'Checking the network configuration.'])
	cursesThread.insertMessage(['informative', ''])

	#Shut down network before getting MAC addresses. Attempting to shutdown even if already shut down is fine.
        command = 'systemctl stop network'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while shutting down the network.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while shutting down the network; thus the network configuration was not confirmed.'
		return errorMessage

	#Sleep to avoid a race condition while the network is shutting down. This is just an extra precatuion.
	time.sleep(30.0)

        #Get the interface and mac address mapping of all NIC cards.
        command = 'ifconfig -a'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Unable to get NIC card information.\n' + err + '\n' + out)
                errorMessage = 'Unable to get NIC card information; thus the network configuration was not confirmed.'
		return errorMessage

        nicDataList = out.splitlines()

        nicDict = {}

        for data in nicDataList:
                if 'HWaddr' in data:
                        try:
                                nicList = re.match('\s*([a-z0-9]+)\s+.*HWaddr\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
                        except AttributeError as err:
                                logger.error('There was a match error when trying to match against \'' + data + '\'.\n' + str(err))
				errorMessage = 'There was a match error when trying to match against \'' + data + '\'; thus the network configuration was not confirmed.'
				return errorMessage

                        nicDict[nicList[1].lower()] = nicList[0]

	logger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')
	
	#Get previous MAC address to NIC mapping.
        try:
		macAddressDataFile = programParentDir + '/nicDataFiles/macAddressData.dat'

                with open(macAddressDataFile) as f:
			macAddressData = f.readlines()
        except IOError as err:
                logger.error('Unable to get the MAC address list from \'' + macAddressDataFile + '\'.\n' + str(err))
		errorMessage = 'Unable to get the MAC address list from \'' + macAddressDataFile + '\'; thus the network configuration was not confirmed.'
		return errorMessage

	macAddressDict = dict(x.strip().split('|') for x in macAddressData)
	macAddressDict = dict(map(reversed, macAddressDict.items()))

	logger.info('The MAC address dictionary was determined to be: ' + str(macAddressDict) + '.')

	#This dictionary containg a mapping between the previous NIC name (key) and current NIC name (value).
	changedNicDict = {}	

	for macAddress in macAddressDict:
		currentNicName = macAddressDict[macAddress]
		previousNicName = nicDict[macAddress]
		
		if currentNicName != previousNicName:
			changedNicDict[previousNicName] = currentNicName

	if len(changedNicDict) != 0:
		errorMessage = updateNICNames(changedNicDict, cursesThread)

	logger.info('Done checking the network configuration.')

	return errorMessage

#End checkNetworkConfiguration(programParentDir, cursesThread):


'''
This function will update the network configuration files based on the 
changed NIC card names.
'''
def updateNICNames(changedNicDict, cursesThread):
	errorMessageList = []

        logger = logging.getLogger('coeOSUpgradeLogger')
	logger.info('Updating the network configuration.')
	cursesThread.insertMessage(['informative', 'Updating the network configuration.'])
	cursesThread.insertMessage(['informative', ''])

	logger.info('The changed NIC dictionary was determined to be: ' + str(changedNicDict) + '.')

	#This is a list of the files that may need to have the NIC name changed.
	networkCfgFileList = []
	
        networkDir = '/etc/sysconfig/network'

	try:
		os.chdir(networkDir)
        except OSError as err:
		logger.error('Unable to change into the network directory \'' + networkDir + '\'.\n' + str(err))
		errorMessage = 'Unable to change into the network directory \'' + networkDir + '\'; thus the network configuration was not confirmed.'
		return errorMessage

	#routes may or may not exist, so we need to check.
	if os.path.isfile('routes'):
		networkCfgFileList.append('routes')

	#Get a list of the NIC configuration files.
        command = 'ls ifcfg-*'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while getting a listing of the NIC configuration files.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while getting a listing of the NIC configuration files; thus the network configuration was not confirmed.'
		return errorMessage

	nicCfgFileList = out.splitlines()

	logger.info('The NIC configuration files were determined to be: ' + str(nicCfgFileList) + '.')

	tmpNicNameDict = dict((nic.strip().replace('ifcfg-', ''), nic.strip()) for nic in nicCfgFileList)

	nicNameDict = {}

	#Make sure there are not files that are extras, e.g.ifroute-em0.BAK, etc.
	for key in tmpNicNameDict:
		if not '.' in key:
			nicNameDict[key] = tmpNicNameDict[key]
			networkCfgFileList.append(tmpNicNameDict[key])

	logger.info('The NIC name dictionary was determined to be: ' + str(nicNameDict) + '.')

	#Get a list of the NIC specific route configuration files.
       	command = 'ls ifroute-*'

	logger.info('The command used to get the list of NIC specific route configuration files was: \'' + command + '\'.')

        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while getting a listing of the NIC specific route configuration files.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while getting a listing of the NIC specific route configuration files; thus the network configuration was not confirmed.'
		return errorMessage

	routeCfgFileList = out.splitlines()

	logger.info('The route configuration filew list was determined to be: ' + str(routeCfgFileList) + '.')

	tmpRouteNicNameDict = dict((route.strip().replace('ifroute-', ''), route.strip()) for route in routeCfgFileList)

	routeNicNameDict = {}

	#Make sure there are not files that are extras, e.g.ifroute-em0.BAK, etc.
	for key in tmpRouteNicNameDict:
		if not '.' in key:
			routeNicNameDict[key] = tmpRouteNicNameDict[key]
			networkCfgFileList.append(tmpRouteNicNameDict[key])

	if len(routeNicNameDict) > 0:
		logger.info('The route name dictionary was determined to be: ' + str(routeNicNameDict) + '.')

	'''
	Move ifcfg-<NICName> and routes files to a file with its new NIC name and update all 
	files with the new name.
	'''
	for nicName in changedNicDict:
		#Update NIC configuration files with the new/changed NIC name.
		command = "sed -i 's/" + nicName + '/' + changedNicDict[nicName] + "/g' " + ' '.join(networkCfgFileList)

		logger.info('The command used to update the NIC configuration files with the new NIC name was: \'' + command + '\'.')

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Problems were encountered while updating the configuration files with the new NIC name \'' + changedNicDict[nicName] + '\'.\n' + err + '\n' + out)
			errorMessage = 'Problems were encountered while updating the configuration files with the new NIC name \'' + changedNicDict[nicName] + '\'; thus the network configuration was not confirmed.'
			return errorMessage

		#Move the NIC configuration file to its new name if the original configuration file exists.
		if nicName in nicCfgFileList:
			command = 'mv ' + nicCfgFileList[nicName] + ' ifcfg-' + changedNicDict[nicName]

			logger.info('The command used to move the NIC configuration files to their new NIC name was: \'' + command + '\'.')

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if result.returncode != 0:
				logger.error('Problems were encountered while moving \'' + nicCfgFileList[nicName] + '\' to \'ifcfg-' + changedNicDict[nicName] + '\'.\n' + err + '\n' + out)
				errorMessage = 'Problems were encountered while moving \'' + nicCfgFileList[nicName] + '\' to \'ifcfg-' + changedNicDict[nicName] + '\'; thus the network configuration was not confirmed.'
				return errorMessage

		#Move the NIC route configuration file to its new name if the original configuration file exists.
		if nicName in routeCfgFileList:
			newRouteFileName = 'ifroute-' + changedNicDict[nicName]

			command = 'mv ' + routeCfgFileList[nicName] + ' ' + newRouteFileName

			logger.info('The command used to move the NIC route configuration files to their new NIC name was: \'' + command + '\'.')

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if result.returncode != 0:
				logger.error('Problems were encountered while moving \'' + routeCfgFileList[nicName] + '\' to \'' + newRouteFileName + '\'.\n' + err + '\n' + out)
				errorMessage = 'Problems were encountered while moving \'' + routeCfgFileList[nicName] + '\' to \'' + newRouteFileName + '\'; thus the network configuration was not confirmed.'
				return errorMessage

	logger.info('Done updating the network configuration.')

	return errorMessage

#End updateNICNames(changedNicDict, cursesThread):


'''
This function restores the HANA user accounts.
'''
def restoreHANAUserAccounts(programParentDir, cursesThread):
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
	logger.info('Restoring SAP HANA user accounts.')
	cursesThread.insertMessage(['informative', 'Restoring SAP HANA user accounts.'])
	cursesThread.insertMessage(['informative', ''])

	userLoginDataDir = programParentDir + '/userLoginData'

	accountFileList = ['group', 'passwd', 'shadow']

	for file in accountFileList:
		accountFile = '/etc/' + file

		command = 'cat ' + userLoginDataDir + '/' + file + ' >> ' + accountFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error('Problems were encountered while adding SAP HANA user accounts to \'' + accountFile + '\'.\n' + err + '\n' + out)
			errorMessage = 'Problems were encountered while adding SAP HANA user accounts to \'' + accountFile + '\'; thus the SAP HANA accounts were not successfully restored.'
			return errorMessage

	logger.info('Done restoring SAP HANA user accounts.')

	return errorMessage

#End restoreHANAUserAccounts(programParentDir, cursesThread):


'''
This function recreates the SAP HANA mount points and restores the SAP HANA entries to fstab.
'''
def restoreHANAPartitionData(programParentDir, cursesThread):
        errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.info('Restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')
        cursesThread.insertMessage(['informative', 'Restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.'])
        cursesThread.insertMessage(['informative', ''])

	fstabDataFile = programParentDir + '/fstabData/fstab'

        #Get group file data.
        command = 'cat ' + fstabDataFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('There was a problem getting the SAP HANA partition data from \'' + fstabDataFile + '\'.\n' + err + '\n' + out)
                errorMessage = 'There was a problem getting the SAP HANA partition data from \'' + fstabDataFile + '\'; thus the SAP HANA partition data was not successfully restored.'
		return errorMessage

        fstabDataList = out.splitlines()

	#Create SAP HANA mount points.
	for partition in fstabDataList:
		partitionList = partition.split()

		try:
			os.makedirs(partitionList[1])
		except OSError as err:
			logger.error('Unable to create the mount point \'' + partitionList[1] + '\'.\n' + str(err))
			errorMessage = 'Unable to create the mount point \'' + partitionList[1] + '\'; thus the SAP HANA partition data was not successfully restored.'
			return errorMessage

	#Restore fstab entries.
	command = 'cat ' + fstabDataFile + ' >> /etc/fstab'

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Problems were encountered while adding SAP HANA mount points to \'/etc/fstab\'.\n' + err + '\n' + out)
		errorMessage = 'Problems were encountered while adding SAP HANA mount points to \'/etc/fstab\'; thus the SAP HANA partition data was not successfully restored.'
		return errorMessage

        logger.info('Done restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')

	return errorMessage

#End restoreHANAPartitionData(programParentDir, cursesThread):


'''
This function installs HPE software utilities that are needed by conrep to be used to update
the server's BIOS as well as software needed by the CSUR application.
'''
def installHPEUtilitySoftware(programParentDir, cursesThread):
        errorMessage = ''
	hpeUtilitySoftwareInstalled = True

	hpeUtilitySoftwareDir = programParentDir + '/hpeUtilitySoftwareRPMS'

        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.info('Installing HPE software utilities needed by conrep and the firmware/driver update.')
        cursesThread.insertMessage(['informative', 'Installing HPE software utilities needed by conrep and the firmware/driver update.'])
        cursesThread.insertMessage(['informative', ''])

	command = 'rpm -Uvh ' + hpeUtilitySoftwareDir + '/*.rpm'

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Problems were encountered while installing HPE software utilities.\n' + err + '\n' + out)
		errorMessage = 'Problems were encountered while installing HPE software utilities; thus the server\'s BIOS was not updated; the RPMS will need to be installed manually before proceeding.'
		hpeUtilitySoftwareInstalled = False
		return errorMessage, hpeUtilitySoftwareInstalled

        logger.info('Done installing HPE software utilities needed by conrep and the firmware/driver update.')

	return errorMessage, hpeUtilitySoftwareInstalled

#End installHPEUtilitySoftware(programParentDir, cursesThread):


'''
This function sets the hostname on servers running SLES.
'''
def setHostname(programParentDir, cursesThread):
        errorMessage = ''

	hostnameFile = programParentDir + '/hostnameData/hostname'

        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.info('Setting the server\'s hostname.')
        cursesThread.insertMessage(['informative', 'Setting the server\'s hostname.'])
        cursesThread.insertMessage(['informative', ''])

        try:
                f = open(hostnameFile, 'r')
                hostname = f.readline()
        except IOError as err:
		logger.error('Problems were encountered while reading the server\'s hostname from \'' + hostnameFile + '\'.\n' + str(err))
		errorMessage = 'Problems were encountered while reading the server\'s hostname from \'' + hostnameFile + '\'; thus the server\'s hostname was not set.'
		return errorMessage

	command = 'hostnamectl set-hostname ' + hostname

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Problems were encountered while setting the server\'s hostname \'' + hostname + '\'.\n' + err + '\n' + out)
		errorMessage = 'Problems were encountered while setting the server\'s hostname \'' + hostname + '\'; thus the server\'s hostname was not set.'
		return errorMessage

        logger.info('Done setting the server\'s hostname.')

	return errorMessage

#End setHostname(programParentDir, cursesThread):


'''
This function is used to print an error message to the user 
and wait for them to press enter to exit the program.
'''
def displayErrorMessage(message, cursesThread):
	cursesThread.insertMessage(['error', message])
	cursesThread.insertMessage(['informative', ''])
	cursesThread.getUserInput(['error', 'Press enter to exit and try again.'])
	cursesThread.insertMessage(['informative', ''])

	while not cursesThread.isUserInputReady():
        	time.sleep(0.1)
	exit(1)

#End displayErrorMessage(message):


'''
This is the main function that calls the other functions to prepare and perform
the pre-upgrade backup.
'''
def main():
	programVersion = '2017.05-rc1'
	hpeUtilitySoftwareInstalled = False

	'''
	The errorMessageList keeps track of errors encountered during the restoration process so that 
	one knows what will have to be done manually if necessary.
	'''
	errorMessageList = []

        #The program can only be ran by root.
        if os.geteuid() != 0:
                print(RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS)
                exit(1)

	#Change into directory containing the program, which should be the mount point of the ISO image containing the files needed for the post upgrade configuration/update.
	try:
		programParentDir = ''

		cwd = os.getcwd()

		programParentDir = os.path.dirname(os.path.realpath(__file__))

		if cwd != programParentDir:
			os.chdir(programParentDir)
	except OSError as err:
		print(RED + 'Unable to change into the programs parent directory \'' + programParentDir + '\'; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
		exit(1)

        #Get the server's OS distribution version information.
        command = 'cat /proc/version'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                print(RED + 'Unable to get the server\'s OS distribution information; fix the problem and try again; exiting program execution.\n' + err + '\n' + out + RESETCOLORS)
                exit(1)

        #Change version information to lowercase before checking for OS type.
        versionInfo = out.lower()

        if not 'suse' in versionInfo:
                print(RED + 'The OS distribution \'' + versionInfo + '\' is not supported; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	#Set and create the upgrade working directory if it does not exist.
        upgradeLogDir = '/var/log/CoE_SAP_HANA_SLES_Upgrade_Log_Dir'

	if not os.path.isdir(upgradeLogDir):
		try:
			os.mkdir(upgradeLogDir)
		except OSError as err:
			print(RED + 'Unable to create the post upgrade log directory \'' + upgradeLogDir + '\'; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
			exit(1)

        #Configure logging.
        dateTimestamp = (datetime.datetime.now()).strftime('%d%H%M%b%Y')

        logFile = upgradeLogDir + '/SLES_Post_Upgrade_' + dateTimestamp + '.log'

        handler = logging.FileHandler(logFile)

        logger = logging.getLogger('coeOSUpgradeLogger')

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	logger.info('The current version of the program is: ' + programVersion + '.')

	#Only Ivy Bridge and Haswell systems are supported for an upgrade.
	processorDict = {'62' : 'ivybridge', '63' : 'haswell'}

        command = 'cat /proc/cpuinfo'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('There was a problem getting the cpu information.\n' + err + '\n' + out)
                print(RED + 'There was a problem getting the cpu information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	cpudata = out.splitlines()

	for line in cpudata:
		if re.match('\s*model\s+:\s+[2-9]{2}', line) != None:
			try:
				processor = processorDict[re.match('\s*model\s+:\s+([2-9]{2})', line).group(1)]
			except AttributeError as err:
				logger.error('There was a match error when trying to match against ' + line + '.\n' + str(err))
				print(RED + 'There was a match error matching against \'' + line + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
				exit(1)
			except KeyError as err:
				logger.error('The resource key (' + str(err) + ') was not present in the processor dictionary.')
				print(RED + 'The server is not supported for an upgrade, since it is not using a Haswell or Ivy Bridge processor; fix the problem and try again; exiting program execution.' + RESETCOLORS)
				exit(1)
			
			break

        #This dictionary holds the resource files resources.
        upgradeResourceDict = {}

        #Get the upgrade resource file data and save it to a dictionary (hash).
        try:
                with open('upgradeResourceFile') as f:
                        for line in f:
                                line = line.strip()

                                #Ignore commented and blank lines.
                                if len(line) == 0 or re.match("^\s*#", line) or re.match('^\s+$', line):
                                        continue
                                else:
                                        #Remove quotes from resources.
                                        line = re.sub('[\'"]', '', line)

                                        (key, val) = line.split('=')
                                        key = key.strip()
                                        upgradeResourceDict[key] = re.sub('\s+', '', val)
        except IOError as err:
                logger.error('Unable to access the application\'s resource file \'upgradeResourceFile\'.\n' + str(err))
                print(RED + 'Unable to access the application\'s resource file \'upgradeResourceFile\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	#Setup curses, so that messages can be scrolled during program execution.
        sessionScreenLog = upgradeLogDir + '/sessionScreenLog.log'
        cursesLog = upgradeLogDir + '/cursesLog.log'

        try:
                '''
                The application uses curses to manage the display so that we have two
                windows. One for feedback and one for conversing.  Also, scrolling is implemented.
                '''
                cursesThread = CursesThread(sessionScreenLog, cursesLog)
                cursesThread.daemon = True
                cursesThread.start()

		'''
		Check to make sure the restoration archive file from the preupgrade is not corrupt.
		Three attempts will be made before using the restoration archive is abandoned.
		'''
		restorationArchiveErrorFile = upgradeLogDir + '/.restorationArchiveError'

		if not os.path.isfile(restorationArchiveErrorFile):
			try:
				os.mknod(restorationArchiveErrorFile)
			except OSError as err:
				logger.error('Unable to create the restoration archive error file \'' + restorationArchiveErrorFile + '\'.\n' + str(err))
				displayErrorMessage('Unable to create the restoration archive error file \'' + restorationArchiveErrorFile + '\'; fix the problem and try again.', cursesThread)

		'''
		The progress status file is used to keep track of what was already done in case the 
		program is ran again. Thus, only those functions that were note already ran will be run.
		'''
		progressStatusFile = upgradeLogDir + '/.restorationProgress'

		try:
			if os.path.isfile(progressStatusFile):
				with open(progressStatusFile) as f:
					progressDict = dict.fromkeys(x.strip() for x in f)
			else:
				progressDict = {}

			if os.path.isfile(progressStatusFile):
				f = open(progressStatusFile, 'a')
			else:
				f = open(progressStatusFile, 'w')

			'''	
			This variable is used to identify if the restoration archive was successfully extracted,
			since it may not be in the progress status file yet, while attempts to extract the archive
			are still being made.
			'''
			restorationArchiveExtracted = False

			try:
				#Check and extract the restoration archive; three attempts are allowed.
				if os.stat(restorationArchiveErrorFile).st_size < 50 and not 'restorationArchiveExtracted' in progressDict:
					cursesThread.insertMessage(['informative', 'Checking and extracting the restoration archive file.'])
					cursesThread.insertMessage(['informative', ''])
					preUpgradeArchive = checkPreupgradeArchive(programParentDir, restorationArchiveErrorFile, cursesThread)
					if extractPreupgradeArchive(preUpgradeArchive, restorationArchiveErrorFile, cursesThread):
						f.write('restorationArchiveExtracted\n')
						restorationArchiveExtracted = True
			except OSError as err:
				logger.error('Unable to access the restoration archive error file \'' + restorationArchiveErrorFile + '\'.\n' + str(err))
				displayErrorMessage('Unable to access the restoration archive error file \'' + restorationArchiveErrorFile + '\'; fix the problem and try again.', cursesThread)

			if not 'setHostname' in progressDict:
				f.write('setHostname\n')

				errorMessage = setHostname(programParentDir, cursesThread)
			
				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)

			if not 'installHPEUtilitySoftware' in progressDict:
				f.write('installHPEUtilitySoftware\n')

				(errorMessage, hpeUtilitySoftwareInstalled)  = installHPEUtilitySoftware(programParentDir, cursesThread)
			
				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)

			if not 'updateBIOS' in progressDict and hpeUtilitySoftwareInstalled:
				f.write('updateBIOS\n')
				errorMessage = updateBIOS(programParentDir, cursesThread)
			
				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)

			if not 'updateOSSettings' in progressDict:
				f.write('updateOSSettings\n')
				osErrorMessageList = updateOSSettings(cursesThread)
			
				if len(osErrorMessageList) > 0:
					errorMessageList += osErrorMessageList

			if not 'installAddOnFiles' in progressDict:
				f.write('installAddOnFiles\n')
				errorMessage = installAddOnFiles(programParentDir, processor, cursesThread)

				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)

			if not 'checkNetworkConfiguration' in progressDict and ('restorationArchiveExtracted' in progressDict or restorationArchiveExtracted):
				f.write('checkNetworkConfiguration\n')
				errorMessage = checkNetworkConfiguration(programParentDir, cursesThread)

				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)

			if not 'restoreHANAUserAccounts' in progressDict:
				f.write('restoreHANAUserAccounts\n')
				errorMessage = restoreHANAUserAccounts(programParentDir, cursesThread)

				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)

			if not 'restoreHANAPartitionData' in progressDict:
				f.write('restoreHANAPartitionData\n')
				errorMessage = restoreHANAPartitionData(programParentDir, cursesThread)

				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)
		except IOError as err:
			logger.error('Could not access ' + progressStatusFile + '.\n' + str(err))
			displayErrorMessage('Could not access \'' + progressStatusFile + '\'; fix the problem and try again.', cursesThread)

		f.close()

		if len(errorMessageList) > 0:
			cursesThread.insertMessage(['warning', 'Restoration of the server has completed with the errors shown below; check the log file for additional information:'])
			cursesThread.insertMessage(['warning', ''])

			for message in errorMessageList:
				cursesThread.insertMessage(['warning', message])
				cursesThread.insertMessage(['warning', ''])
		else:
			cursesThread.insertMessage(['informative', 'Restoration of the server has completed; check log files and perform a functional check before turning the server back over to the customer.'])
			cursesThread.insertMessage(['informative', ''])
	
		cursesThread.getUserInput(['informative', 'Press enter to exit the program.'])
		cursesThread.insertMessage(['informative', ''])

		while not cursesThread.isUserInputReady():
			time.sleep(0.1)
		exit(0)

        except Exception:
                cursesThread.join()
                traceback.print_exc()
                exit(1)
        finally:
                cursesThread.join()
	
#End main():

main()
