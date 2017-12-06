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
The purpose of this script is restore OS configuration after a RHEL 7.2
upgrade is performed.

Author Bill Neumann
'''

def checkOSRestorationArchive(programParentDir, osRestorationArchiveErrorFile, cursesThread):
	osRestorationArchiveFile = ''

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Checking the OS restoration archive to make sure it is not corrupt.')

	osArchiveFileRegex = re.compile('.*_OS_Restoration_Backup_For_RHEL_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')

	archiveImageDir = programParentDir + '/archiveImages'

        command = 'ls ' + archiveImageDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Unable to get a listing of the files in \'' + archiveImageDir + '\'.\n' + err + '\n' + out)
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
		displayErrorMessage('Unable to get a listing of the files in \'' + archiveImageDir + '\'; fix the problem and try again.', cursesThread)

	fileList = out.splitlines()

	osRestorationArchiveFound = False

	for file in fileList:
		if re.match(osArchiveFileRegex, file):
			md5sumFile = re.sub('tar.gz', 'md5sum', file)
			osRestorationArchiveFile = archiveImageDir + '/' + file
			osRestorationArchiveMd5sumFile = archiveImageDir + '/' + md5sumFile
			osRestorationArchiveFound = True
			break

	if not osRestorationArchiveFound:
                logger.error('The OS restoration archive \'' + archiveImageDir + '/' + osArchiveFileRegex.pattern + '\' could not be found.')
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
		displayErrorMessage('The OS restoration archive \'' + archiveImageDir + '/' + osArchiveFileRegex.pattern + '\' could not be found; fix the problem and try again.', cursesThread)

	if not os.path.isfile(osRestorationArchiveMd5sumFile):
                logger.error('The OS restoration archive\'s md5sum file \'' + osRestorationArchiveMd5sumFile + '\' is missing.')
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
                displayErrorMessage('The OS restoration archive\'s md5sum file \'' + osRestorationArchiveMd5sumFile + '\' is missing; fix the problem and try again.', cursesThread)

        command = 'md5sum ' + osRestorationArchiveFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Unable to determine the md5sum of the OS restoration archive \'' + osRestorationArchiveFile + '\'.\n' + err + '\n' + out)
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
                displayErrorMessage('Unable to determine the md5sum of the OS restoration archive \'' + osRestorationArchiveFile + '\'; fix the problem and try again.', cursesThread)

	try:
        	osRestorationArchiveMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)
	except AttributeError as err:
		logger.error('There was a match error when trying to match against ' + out + '.\n' + str(err))
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
		displayErrorMessage('There was a match error when matching against \'' + out + '\'; fix the problem and try again.', cursesThread)

        try:
                with open(osRestorationArchiveMd5sumFile) as f:
                        for line in f:
                                line = line.strip()
                                if file in line:
                                        originalOSRestorationArchiveMd5sum = re.match('([0-9,a-f]*)\s+', line).group(1)
        except IOError as err:
                logger.error('Unable to get the md5sum of the OS restoration archive from \'' + osRestorationArchiveMd5sumFile + '\'.\n' + str(err))
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
                displayErrorMessage('Unable to get the md5sum of the OS restoration archive from \'' + osRestorationArchiveMd5sumFile + '\'; fix the problem and try again.', cursesThread)
	except AttributeError as err:
		logger.error('There was a match error when trying to match against \'' + line + '\'.\n' + str(err))
		updateOSestorationArchiveErrorFile(osRestorationArchiveErrorFile)
		displayErrorMessage('There was a match error when matching against \'' + line + '\'; fix the problem and try again.', cursesThread)

        if osRestorationArchiveMd5sum != originalOSRestorationArchiveMd5sum:
                logger.error('The OS restoration archive \'' + osRestorationArchiveFile + '\' is corrupt; its md5sum does not match its md5sum in \'' + osRestorationArchiveMd5sumFile + '\'.')
		updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
                displayErrorMessage('The OS restoration archive \'' + osRestorationArchiveFile + '\' is corrupt; fix the problem and try again.', cursesThread)

	logger.info('Done checking the OS restoration archive to make sure it is not corrupt.')

	return osRestorationArchiveFile

#End checkOSRestorationArchive(programParentDir, osRestorationArchiveErrorFile, cursesThread):


'''
This function extracts the OS restoration archive file.
'''
def extractOSRestorationArchive(osRestorationArchive, osRestorationArchiveErrorFile, cursesThread):
	osRestorationArchiveExtracted = True

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Extracting the OS restoration archive image.')

        command = 'tar -zxf ' + osRestorationArchive + ' -C /'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.info('The command used to extract the OS restoration archive was: \'' + command + '\'.')

        if result.returncode != 0:
                logger.error('There was a problem extracting the OS restoration archive \'' + osRestorationArchive + '\'.\n' + err + '\n' + out)
		updateRestorationArchiveErrorFile(restorationArchiveErrorFile)
                displayErrorMessage('There was a problem extracting the os restoration archive \'' + osRestorationArchive + '\'; fix the problem and try again.', cursesThread)
		osRestorationArchiveExtracted = False

	logger.info('Done extracting the OS restoration archive image.')

	return osRestorationArchiveExtracted

#End extractOSRestorationArchive(osRestorationArchive, osRestorationArchiveErrorFile, cursesThread):


'''
This function updates the OS restoration archive error file, which is used to keep track of the number of attempts
to extract the archive.
'''
def updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile):
        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Updating the OS restoration archive error file with an archive failure attempt.')

	try:
		f = open(osRestorationArchiveErrorFile, 'a')

		if os.stat(osRestorationArchiveErrorFile).st_size == 0:
			f.write('First Attempt Failed\n')
		elif os.stat(osRestorationArchiveErrorFile).st_size  < 25:
			f.write('Second Attempt Failed\n')
		elif os.stat(osRestorationArchiveErrorFile).st_size  < 45:
			f.write('Third Attempt Failed\n')
	except IOError as err:
		logger.error('Could not write to the OS restoration archive error file ' + osRestorationArchiveErrorFile + '.\n' + str(err))
                displayErrorMessage('Could not write to the OS restoration archive error file \'' + osRestorationArchiveErrorFile + '\'; fix the problem and try again.', cursesThread)

	f.close()

	logger.info('Done updating the restoration archive error file with an archive failure attempt.')

#End updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile):


'''
This function extracts the sap restoration archive file.
'''
def extractSAPRestorationArchive(programParentDir, cursesThread):
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Extracting the SAP restoration archive.')
	cursesThread.insertMessage(['informative', 'Extracting the SAP restoration archive.'])
	cursesThread.insertMessage(['informative', ''])

	sapArchiveFileRegex = re.compile('.*_SAP_Restoration_Backup_For_RHEL_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')

	archiveImageDir = programParentDir + '/archiveImages'

        command = 'ls ' + archiveImageDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Unable to get a listing of the files in \'' + archiveImageDir + '\'.\n' + err + '\n' + out)
		errorMessage = 'Unable to get a listing of the files in \'' + archiveImageDir + '\'; thus the SAP restoration archive was not extracted.'
		return errorMessage

	fileList = out.splitlines()

	sapRestorationArchiveFound = False

	for file in fileList:
		if re.match(sapArchiveFileRegex, file):
			sapRestorationArchive = archiveImageDir + '/' + file
			sapRestorationArchiveFound = True
			break

	if not sapRestorationArchiveFound:
                logger.error('The SAP restoration archive \'' + archiveImageDir + '/' + sapArchiveFileRegex.pattern + '\' could not be found.')
                errorMessage = 'The SAP restoration archive \'' + archiveImageDir + '/' + sapArchiveFileRegex.pattern + '\' could not be found.'
		return errorMessage

        command = 'tar -zxf ' + sapRestorationArchive + ' -C /'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

	logger.info('The command used to extract the SAP restoration archive was: \'' + command + '\'.')

        if result.returncode != 0:
                logger.error('There was a problem extracting the SAP restoration archive \'' + sapRestorationArchive + '\'.\n' + err + '\n' + out)
                errorMessage = 'There was a problem extracting the SAP restoration archive \'' + sapRestorationArchive + '\'.'
		return errorMessage

	logger.info('Done extracting the SAP restoration archive.')

	return errorMessage

#End extractSAPRestorationArchive(programParentDir, cursesThread):


'''
This function upgrades the server's BIOS settings using a predetermined conrep file.
'''
def updateBIOS(programParentDir, cursesThread):
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Updating the server\'s BIOS.')
	cursesThread.insertMessage(['informative', 'Updating the server\'s BIOS.'])
	cursesThread.insertMessage(['informative', ''])

	command = 'conrep -l -f ' + programParentDir + '/conrepFile/conrep.dat'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.info('The command used to update the server\'s BIOS was: \'' + command + '\'.')

	if result.returncode != 0:
		logger.error('An error was encountered while updating the server\'s BIOS.\n' + err + '\n' + out)
		errorMessage = 'An error was encountered while updating the server\'s BIOS.'
		return errorMessage
	
	logger.info('Done updating the server\'s BIOS.')

	return errorMessage

#End updateBIOS(programParentDir, cursesThread):


'''
This function upgrades the server's OS settings according to the following SAP Notes:
	- SAP Note 2292690 - SAP HANA DB Recommended OS settings for RHEL 
'''
def updateOSSettings(cursesThread):
	errorMessageList = []

        logger = logging.getLogger('coeOSUpgradeLogger')

	logger.info('Updating the server\'s OS settings according to SAP Note 2292690.')
	cursesThread.insertMessage(['informative', 'Updating the server\'s OS settings according to SAP Note 2292690.'])
	cursesThread.insertMessage(['informative', ''])

	#Update grub with proper C-States settings.
	updateMade = False

	grubCfgFile = '/etc/default/grub'

	try:
		with open(grubCfgFile) as f:
			for line in f:
				line = line.strip()

				if re.match('\s*GRUB_CMDLINE_LINUX=', line) != None:
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
		command = "sed -i 's|^\s*GRUB_CMDLINE_LINUX=.*|" + grubDefault + "|' " + grubCfgFile

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.info('The command used to update grub\'s default configuration file \'' + grubCfgFile + '\' C-States was: \'' + command + '\'.')

		if result.returncode != 0:
			logger.error('Could not update the C-States settings in \'' + grubCfgFile + '\'.\n' + err + '\n' + out)
			errorMessageList.append('Could not update the C-States settings in ' + grubCfgFile + '.')
		else:
			bootGrubCfgFile = '/boot/efi/EFI/redhat/grub.cfg'

			command = 'grub2-mkconfig -o ' + bootGrubCfgFile
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.info('The command used to generate a new grub.cfg file was: \'' + command + '\'.')

			if result.returncode != 0:
				logger.error('Could not update the GRUB2 configuration with the updated C-States settings.\n' + err + '\n' + out)
				errorMessageList.append('Could not update the GRUB2 configuration with the updated C-States settings.')

	logger.info('Done updating the server\'s OS settings according to SAP Note 2292690.')

	return errorMessageList

#End updateOSSettings(cursesThread):


'''
This function installs/resplaces additional files.
'''
def installAddOnFiles(programParentDir, upgradeResourceDict, processor, cursesThread):
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
	logger.info('Installing/replacing the files from the add-on archive.')
	cursesThread.insertMessage(['informative', 'Installing/replacing the files from the add-on archive.'])
	cursesThread.insertMessage(['informative', ''])

	if processor == 'ivybridge':
		addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['ivyBridgeRHELAddOnFileArchive']
	else:
		addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['haswellRHELAddOnFileArchive']
	
	command = 'tar -zxf ' + addOnFileArchive + ' -C /'
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('An error was encountered while installing/replacing the files from the add-on file archive.\n' + err + '\n' + out)
		errorMessage = 'An error was encountered while installing/replacing the files from the add-on file archive.'
		return errorMessage

	logger.info('Done installing/replacing the files from the add-on archive.')

	return errorMessage

#End installAddOnFiles(programParentDir, upgradeResourceDict, processor, cursesThread):


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

	#Shut down network before proceeding. Attempting to shutdown even if already shut down is fine.
        command = 'systemctl stop network'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while shutting down the network.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while shutting down the network; thus the network configuration was not confirmed.'
		return errorMessage

	#Unload and reload tg3 driver so that the restored NIC configuration files are referenced.  Thus updating NIC names.
        command = 'modprobe -r tg3'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while unloading the tg3 driver.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while unloading the tg3 driver; thus the network configuration was not confirmed.'
		return errorMessage

	time.sleep(2.0)	

        command = 'modprobe tg3'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while reloading the tg3 driver.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while reloading the tg3 driver; thus the network configuration was not confirmed.'
		return errorMessage

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

	#Keep track of when a valid NIC is found.
	count = 0

	#If a bonding interface is encountered then skip the next ether line.
	skip = False

        for data in nicDataList:
                if 'flags=' in data and not ('lo:' in data or 'bond' in data):
                        try:
                                nicName = re.match('\s*([a-z0-9]+):', data, re.IGNORECASE).group(1)
				count += 1
                        except AttributeError as err:
                                logger.error('There was a match error when trying to match against \'' + data + '\'.\n' + str(err))
				errorMessage = 'There was a match error when trying to match against \'' + data + '\'; thus the network configuration was not confirmed.'
				return errorMessage
                elif 'flags=' in data and 'bond' in data:
			skip = True
		elif 'ether' in data and 'txqueuelen' in data and not skip:
                        try:
				nicMACAddress = re.match('\s*ether\s+([a-z0-9:]+)', data, re.IGNORECASE).group(1)
				count += 1
                        except AttributeError as err:
                                logger.error('There was a match error when trying to match against \'' + data + '\'.\n' + str(err))
				errorMessage = 'There was a match error when trying to match against \'' + data + '\'; thus the network configuration was not confirmed.'
				return errorMessage
		elif 'ether' in data and 'txqueuelen' in data:
			skip = False
		else:
			continue

		if count == 2:
                        nicDict[nicMACAddress] = nicName
			count = 0

	logger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')
	
	#Get previous MAC address to NIC mapping.
        try:
		macAddressDataFile = programParentDir + '/nicDataFile/macAddressData.dat'

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
	
		try:
			previousNicName = nicDict[macAddress]
		except KeyError as err:
			logger.error('The resource key (' + str(err) + ') was not present in the previous NIC dictionary.')
			errorMessage = 'The resource key (' + str(err) + ') was not present in the previous NIC dictionary; thus the network configuration was not confirmed.'
			return errorMessage
		
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
	errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
	logger.info('Updating the network configuration.')
	cursesThread.insertMessage(['informative', 'Updating the network configuration.'])
	cursesThread.insertMessage(['informative', ''])

	logger.info('The changed NIC dictionary was determined to be: ' + str(changedNicDict) + '.')

	#This is a list of the files that may need to have the NIC name changed.
	networkCfgFileList = []
	
	networkDir = '/etc/sysconfig/network-scripts'

	try:
		os.chdir(networkDir)
        except OSError as err:
		logger.error('Unable to change into the network directory \'' + networkDir + '\'.\n' + str(err))
		errorMessage = 'Unable to change into the network directory \'' + networkDir + '\'; thus the network configuration was not confirmed.'
		return errorMessage

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
        command = 'ls route-*'

	logger.info('The command used to get the list of NIC specific route configuration files was: \'' + command + '\'.')

        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while getting a listing of the NIC specific route configuration files.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while getting a listing of the NIC specific route configuration files; thus the network configuration was not confirmed.'
		return errorMessage

	routeCfgFileList = out.splitlines()

	logger.info('The route configuration filew list was determined to be: ' + str(routeCfgFileList) + '.')

	tmpRouteNicNameDict = dict((route.strip().replace('route-', ''), route.strip()) for route in routeCfgFileList)

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
			newRouteFileName = 'route-' + changedNicDict[nicName]

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
	hanaPartitionRestored = False

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
		return errorMessage, hanaPartitionRestored

        fstabDataList = out.splitlines()

	#Create SAP HANA mount points.
	for partition in fstabDataList:
		partitionList = partition.split()

		partition = partitionList[1]

		if partition == '/usr/sap':
			continue

		if not os.path.isdir(partition):
			try:
				os.makedirs(partition)
			except OSError as err:
				logger.error('Unable to create the mount point \'' + partition + '\'.\n' + str(err))
				errorMessage = 'Unable to create the mount point \'' + partition + '\'; thus the SAP HANA partition data was not successfully restored.'
				return errorMessage, hanaPartitionRestored

	#Restore fstab entries.
	command = 'cat ' + fstabDataFile + ' >> /etc/fstab'

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Problems were encountered while adding SAP HANA mount points to \'/etc/fstab\'.\n' + err + '\n' + out)
		errorMessage = 'Problems were encountered while adding SAP HANA mount points to \'/etc/fstab\'; thus the fstab file was not updated.'
		return errorMessage, hanaPartitionRestored
	else:
		hanaPartitionRestored = True

	#Need to mount /usr/sap before the SAP archive is extracted.
	command = 'mount /usr/sap'

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error('Problems were encountered while mounting \'/usr/sap\'.\n' + err + '\n' + out)
		errorMessage = 'Problems were encountered while mounting \'/usr/sap\'; thus the SAP HANA partition data was not successfully restored.'
		hanaPartitionRestored = False
		return errorMessage, hanaPartitionRestored

        logger.info('Done restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')

	return errorMessage, hanaPartitionRestored

#End restoreHANAPartitionData(programParentDir, cursesThread):


'''
This function installs additional software RPMS that are needed for the upgrade.
'''
def installAddOnSoftware(programParentDir, cursesThread):
        errorMessage = ''
        addOnSoftwareInstalled = True

        addOnSoftwareDir = programParentDir + '/addOnSoftwareRPMS'

        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.info('Installing the additional software RPMS needed for the upgrade.')
        cursesThread.insertMessage(['informative', 'Installing the additional software RPMS needed for the upgrade.'])
        cursesThread.insertMessage(['informative', ''])

        command = 'rpm -Uvh ' + addOnSoftwareDir + '/*.rpm'

        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while installing the additional software RPMS.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while installing the additional software RPMS; the RPMS will need to be installed manually before proceeding.'
                addOnSoftwareInstalled = False
                return errorMessage, addOnSoftwareInstalled

        logger.info('Done installing the additional software RPMS needed for the upgrade.')

        return errorMessage, addOnSoftwareInstalled

#End installAddOnSoftware(programParentDir, cursesThread):


'''
This function disables multipathd.
'''
def disableMultipathd(cursesThread):
        errorMessage = ''

        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.info('Disabling multipathd, since the server is not part of a CS500 Scale-out system.')
        cursesThread.insertMessage(['informative', 'Disabling multipathd, since the server is not part of a CS500 Scale-out system.'])
        cursesThread.insertMessage(['informative', ''])

        command = 'systemctl disable multipathd'

        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while disabling multipathd.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while disabling multipathd.'
                return errorMessage

        logger.info('Done disabling multipathd, since the server is not part of a CS500 Scale-out system.')

        return errorMessage

#End disableMultipathd(cursesThread):


'''
This function updates the tuning profile to be sap-hpe-hana.
'''
def updateTuningProfile(cursesThread):
        errorMessage = ''
	tuningProfile = 'sap-hpe-hana'

        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.info('Updating the OS\'s tuning profile to be \'' + tuningProfile + '\'.')
        cursesThread.insertMessage(['informative', 'Updating the OS\'s tuning profile to be \'' + tuningProfile + '\'.'])
        cursesThread.insertMessage(['informative', ''])

        command = 'tuned-adm profile ' + tuningProfile

        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()

        if result.returncode != 0:
                logger.error('Problems were encountered while updating the OS\'s tuning profile to be \'' + tuningProfile + '\'.\n' + err + '\n' + out)
                errorMessage = 'Problems were encountered while updating the OS\'s tuning profile to be \'' + tuningProfile + '\'.'
                return errorMessage

        logger.info('Done updating the OS\'s tuning profile to be \'' + tuningProfile + '\'.')

        return errorMessage

#End updateTuningProfile(cursesThread):


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
	addOnSoftwareInstalled = False
	hanaPartitionsRestored = False

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

        if not 'redhat' in versionInfo:
                print(RED + 'The OS distribution \'' + versionInfo + '\' is not supported; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	#Set and create the upgrade log directory if it does not exist.
        upgradeLogDir = '/var/log/CoESapHANA_RHEL_UpgradeLogDir'

	if not os.path.isdir(upgradeLogDir):
		try:
			os.mkdir(upgradeLogDir)
		except OSError as err:
			print(RED + 'Unable to create the post upgrade log directory \'' + upgradeLogDir + '\'; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS)
			exit(1)

        #Configure logging.
        dateTimestamp = (datetime.datetime.now()).strftime('%d%H%M%b%Y')

        logFile = upgradeLogDir + '/RHEL_Post_Upgrade_' + dateTimestamp + '.log'

        handler = logging.FileHandler(logFile)

        logger = logging.getLogger('coeOSUpgradeLogger')

        logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	logger.info('The current version of the program is: ' + programVersion + '.')

        #Get the server's model, since we don't perform SAP HANA related tasks on Serviceguard servers.
        command = 'dmidecode -s system-product-name'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        out = out.strip()

        if result.returncode != 0:
                logger.error('Unable to get the server\'s model information.\n' + err + '\n' + out)
                print(RED + 'Unable to get the server\'s model information; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

        logger.info('The server\'s model was determined to be: ' + out + '.')

        try:
                serverModel = (re.match('[a-z,0-9]+\s+(.*)', out, re.IGNORECASE).group(1)).replace(' ', '')
        except AttributeError as err:
                logger.error('There was a server model match error when trying to match against \'' + out + '\'.\n' + str(err))
                print(RED + 'There was a server model match error when trying to match against \'' + out + '\'; fix the problem and try again; exiting program execution.' + RESETCOLORS)
                exit(1)

	
	#The variable is used to determine if a compute node (DL580) is a Scale-up server, which means multipathd needs to be disabled.
	disableMultipathd = False

	if 'DL580' in serverModel:
		command = 'lspci|grep \'Fibre Channel\''
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()
		out = out.strip()

		if result.returncode == 0:
			disableMultipathd = True

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
                cursesThread = CursesThread(sessionScreenLog, cursesLog)
                cursesThread.daemon = True
                cursesThread.start()

		'''
		Check to make sure the OS restoration archive file from the preupgrade is not corrupt.
		Three attempts will be made before using the OS restoration archive is abandoned.
		'''
		osRestorationArchiveErrorFile = upgradeLogDir + '/.osRestorationArchiveError'

		if not os.path.isfile(osRestorationArchiveErrorFile):
			try:
				os.mknod(osRestorationArchiveErrorFile)
			except OSError as err:
				logger.error('Unable to create the OS restoration archive error file \'' + osRestorationArchiveErrorFile + '\'.\n' + str(err))
				displayErrorMessage('Unable to create the OS restoration archive error file \'' + osRestorationArchiveErrorFile + '\'; fix the problem and try again.', cursesThread)

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
			This variable is used to identify if the OS restoration archive was successfully extracted,
			since it may not be in the progress status file yet, while attempts to extract the archive
			are still being made.
			'''
			osRestorationArchiveExtracted = False

			try:
				#Check and extract the OS restoration archive; three attempts are allowed.
				if os.stat(osRestorationArchiveErrorFile).st_size < 50 and not 'osRestorationArchiveExtracted' in progressDict:
					cursesThread.insertMessage(['informative', 'Checking and extracting the OS restoration archive file.'])
					cursesThread.insertMessage(['informative', ''])
					osRestorationArchive = checkOSRestorationArchive(programParentDir, osRestorationArchiveErrorFile, cursesThread)
					if extractOSRestorationArchive(osRestorationArchive, osRestorationArchiveErrorFile, cursesThread):
						f.write('osRestorationArchiveExtracted\n')
						osRestorationArchiveExtracted = True
			except OSError as err:
				logger.error('Unable to access the OS restoration archive error file \'' + osRestorationArchiveErrorFile + '\'.\n' + str(err))
				displayErrorMessage('Unable to access the OS restoration archive error file \'' + osRestorationArchiveErrorFile + '\'; fix the problem and try again.', cursesThread)

			if not 'installaddOnSoftware' in progressDict:
				f.write('installaddOnSoftware\n')

				(errorMessage, addOnSoftwareInstalled)  = installAddOnSoftware(programParentDir, cursesThread)
			
				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)
			else:
					errorMessageList.append('The additional RPMS were not installed, since an attempt in add them was already made.')

			if not 'updateBIOS' in progressDict and addOnSoftwareInstalled:
				f.write('updateBIOS\n')
				errorMessage = updateBIOS(programParentDir, cursesThread)
			
				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)
			else:
					errorMessageList.append('The server\'s BIOS was not updated; either because it was already updated or the additional RPMS failed to install.')

			if not 'installAddOnFiles' in progressDict:
				f.write('installAddOnFiles\n')
				errorMessage = installAddOnFiles(programParentDir, upgradeResourceDict.copy(), processor, cursesThread)

				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)
			else:
					errorMessageList.append('The files from the add on files archive were not installed, since an attempt in add them was already made.')

			if not 'checkNetworkConfiguration' in progressDict and ('osRestorationArchiveExtracted' in progressDict or osRestorationArchiveExtracted):
				f.write('checkNetworkConfiguration\n')
				errorMessage = checkNetworkConfiguration(programParentDir, cursesThread)

				if len(errorMessage) > 0:
					errorMessageList.append(errorMessage)
			else:
					errorMessageList.append('The server\'s network configuration was not checked; either because it was already checked or the OS restoration archive was not successfully extracted.')

			#This section is for compute nodes; not Serviceguard nodes.
			if not ('DL380' in serverModel or 'DL320' in serverModel or 'DL360' in serverModel):
				if not 'updateOSSettings' in progressDict:
					f.write('updateOSSettings\n')
					osErrorMessageList = updateOSSettings(cursesThread)
				
					if len(osErrorMessageList) > 0:
						errorMessageList += osErrorMessageList
				else:
						errorMessageList.append('The SAP HANA DB recommeneded OS settings were not updated, since an attempt to update the settings was already made.')

				if not 'restoreHANAUserAccounts' in progressDict:
					f.write('restoreHANAUserAccounts\n')
					errorMessage = restoreHANAUserAccounts(programParentDir, cursesThread)

					if len(errorMessage) > 0:
						errorMessageList.append(errorMessage)
				else:
						errorMessageList.append('The SAP HANA user account data was not restored, since an attempt to restore the account data was already made.')

				if not 'restoreHANAPartitionData' in progressDict:
					f.write('restoreHANAPartitionData\n')
					(errorMessage, hanaPartitionsRestored) = restoreHANAPartitionData(programParentDir, cursesThread)

					if len(errorMessage) > 0:
						errorMessageList.append(errorMessage)
				else:
						errorMessageList.append('The SAP HANA parition data was not restored, since an attempt to restore the data was already made.')

				if not 'sapRestorationArchiveExtracted' in progressDict and hanaPartitionsRestored:
					f.write('sapRestorationArchiveExtracted\n')

					errorMessage = extractSAPRestorationArchive(programParentDir, cursesThread)

					if len(errorMessage) > 0:
						errorMessageList.append(errorMessage)
				else:
						errorMessageList.append('The SAP restoration archive was not extracted; either because it was already extracted or the SAP HANA partition data was not successfully restored.')

				if disableMultipathd:
					if not 'disableMultipathd' in progressDict:
						f.write('disableMultipathd\n')

						errorMessage = disableMultipathd(cursesThread)

						if len(errorMessage) > 0:
							errorMessageList.append(errorMessage)
					else:
							errorMessageList.append('multipathd was not disabled, since an attempt to disable it was already made.')

				if not 'updateTuningProfile' in progressDict and addOnSoftwareInstalled:
					f.write('updateTuningProfile\n')
					errorMessage = updateTuningProfile(cursesThread)

					if len(errorMessage) > 0:
						errorMessageList.append(errorMessage)
				else:
						errorMessageList.append('The server\'s tuning profile was not updated; either because it was already updated or the additional RPMS failed to install.')
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
